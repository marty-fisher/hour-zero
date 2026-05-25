import argparse
import os
import json
import psycopg2
from dotenv import load_dotenv

def export_active_reel(output_path):
    # Try to load from .env file first (for local development)
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        
    db_url = os.getenv('SUPABASE_DB_URL')
    
    if not db_url:
        print("Error: SUPABASE_DB_URL not found in environment or .env file.")
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # 1. Fetch active reel metadata
    cur.execute("""
        SELECT active_reel_id FROM public.tracking_state WHERE id = 1;
    """)
    active_id = cur.fetchone()[0]
    if not active_id:
        print("No active reel being tracked.")
        payload = {"status": "no_active_reel"}
        write_json(output_path, payload)
        return

    # 2. Extract series of binned velocities
    query = """
        SELECT
            EXTRACT(EPOCH FROM (p.polled_at - r.posted_at))::INT / 60 AS age_minutes,
            p.velocity,
            r.caption,
            r.posted_at,
            p.views
        FROM public.poll_metrics p
        JOIN public.reels r ON p.reel_id = r.id
        WHERE p.reel_id = %s
        ORDER BY p.polled_at ASC;
    """
    cur.execute(query, (active_id,))
    rows = cur.fetchall()
    
    # 3. Mitigate "Data Gulps" (Smoothing CDN Cache Zero-Bounces)
    # Distribute large spikes across the preceding zero-velocity minutes
    smoothed_points = []
    zero_accum = 0
    
    for r in rows:
        age_m = r[0]
        vel = r[1]
        views = r[4]
        
        if vel == 0:
            zero_accum += 1
            smoothed_points.append({"age_minutes": age_m, "velocity": 0.0, "views": views})
        else:
            if zero_accum > 0:
                distributed_vel = vel / (zero_accum + 1)
                # Apply evenly across previous 0 velocity minutes + current minute
                for i in range(len(smoothed_points) - zero_accum, len(smoothed_points)):
                    smoothed_points[i]["velocity"] = distributed_vel
                # Add the current point
                smoothed_points.append({"age_minutes": age_m, "velocity": distributed_vel, "views": views})
                zero_accum = 0
            else:
                smoothed_points.append({"age_minutes": age_m, "velocity": vel, "views": views})
    
    # 24-hour Projection
    # Uses accumulated views + projected decay of current velocity
    if smoothed_points and rows:
        current_views = rows[-1][4]
        current_age_minutes = smoothed_points[-1]["age_minutes"]
        remaining_minutes = max(0, 1440 - current_age_minutes)
        
        # Determine dynamically decaying half-life by comparing the 15m segments sequentially
        def calculate_decay_constant(target_points):
            import math
            baseline_half_life = 590.0
            if not target_points:
                return math.log(2) / baseline_half_life
                
            # recent 15m segment
            recent_15 = target_points[-15:]
            v_recent = sum(p["velocity"] for p in recent_15) / len(recent_15) if recent_15 else 0
            
            # previous 15m segment
            past_15 = target_points[-30:-15]
            v_past = sum(p["velocity"] for p in past_15) / len(past_15) if past_15 else 0
            
            # Segment-based Momentum Ratio
            if v_past > 0:
                momentum = v_recent / v_past
                # If velocity is decelerating, penalize the ratio quadratically to crash "Flash in the Pan" spikes
                if momentum < 1.0:
                    momentum = momentum ** 2
            else:
                momentum = 1.0 # If no previous segment vs current, base model applies
                
            # Clamp momentum to handle extreme drops, lowering bottom limit to 0.05 (~30m half-life)
            momentum = max(0.05, min(momentum, 3.0))
            
            # Establish decay rate based on previous cumulative segment acceleration
            half_life_minutes = baseline_half_life * momentum
            
            return math.log(2) / half_life_minutes

        # Lookback window for velocity: average the last 15 minutes of velocity.
        recent_points = smoothed_points[-15:]
        if recent_points:
            current_velocity = sum(p["velocity"] for p in recent_points) / len(recent_points)
        else:
            current_velocity = 0
            
        import math
        
        decay_constant = calculate_decay_constant(smoothed_points)
        
        # Integral of exponential decay V(t) = V0 * e^(-k*t) from 0 to remaining_minutes
        # = (V0 / k) * (1 - e^(-k*remaining_minutes))
        if decay_constant > 0:
            accumulated_future_views = (current_velocity / decay_constant) * (1 - math.exp(-decay_constant * remaining_minutes))
        else:
            accumulated_future_views = current_velocity * remaining_minutes
            
        projected_final_views = current_views + accumulated_future_views
        
        # Generate historical predictions (15m, 30m, 45m)
        def predict_at_minute(target_minute):
            target_points = [p for p in smoothed_points if p["age_minutes"] <= target_minute]
            # Find nearest row to get views at that time
            target_row = next((r for r in reversed(rows) if r[0] <= target_minute), None)
            
            if not target_points or not target_row:
                return None
                
            hist_views = target_row[4]
            hist_recent = target_points[-15:]
            if hist_recent:
                hist_velocity = sum(p["velocity"] for p in hist_recent) / len(hist_recent)
            else:
                hist_velocity = 0
                
            hist_remaining = max(0, 1440 - target_minute)
            hist_decay_constant = calculate_decay_constant(target_points)
            
            # Apply same decay logic internally
            if hist_decay_constant > 0:
                hist_future_views = (hist_velocity / hist_decay_constant) * (1 - math.exp(-hist_decay_constant * hist_remaining))
            else:
                hist_future_views = hist_velocity * hist_remaining
                
            return hist_views + hist_future_views

        pred_15m = predict_at_minute(15)
        pred_30m = predict_at_minute(30)
        pred_45m = predict_at_minute(45)
        pred_60m = predict_at_minute(60)

    else:
        current_views = 0
        current_age_minutes = 0
        projected_final_views = 0
        pred_15m = None
        pred_30m = None
        pred_45m = None
        pred_60m = None
    
    caption = rows[0][2] if rows else ""
    posted_at = rows[0][3].isoformat() if rows and rows[0][3] else ""
    
    payload = {
        "reel_id": active_id,
        "caption": caption,
        "posted_at": posted_at,
        "current_trajectory": smoothed_points,
        "current_views": current_views,
        "age_minutes": current_age_minutes,
        "24h_predicted_views": projected_final_views,
        "predictions": {
            "15m": pred_15m,
            "30m": pred_30m,
            "45m": pred_45m,
            "60m": pred_60m,
            "current": projected_final_views
        },
        "last_updated_minutes": rows[-1][0] if rows else None
    }
    
    write_json(output_path, payload)
    print(f"✅ Exported static payload to {output_path}")
    conn.close()

def write_json(output_path, payload):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(payload, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export active reel analytics for Static Web Server")
    parser.add_argument("--output", type=str, required=True, help="Output JSON path")
    args = parser.parse_args()
    export_active_reel(args.output)
