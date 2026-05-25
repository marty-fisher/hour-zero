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
            p.velocity
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
        
        if vel == 0:
            zero_accum += 1
            smoothed_points.append({"age_minutes": age_m, "velocity": 0.0}) # placeholder
        else:
            if zero_accum > 0:
                # We have a gulp. Distribute its velocity evenly over this minute + the preceding zero minutes
                distributed_vel = vel / (zero_accum + 1)
                # Update the preceding placeholders
                for i in range(len(smoothed_points) - zero_accum, len(smoothed_points)):
                    smoothed_points[i]["velocity"] = distributed_vel
                # Add the current point
                smoothed_points.append({"age_minutes": age_m, "velocity": distributed_vel})
                zero_accum = 0
            else:
                smoothed_points.append({"age_minutes": age_m, "velocity": vel})
    
    # Simple projection (Archetype Shape matching placeholder)
    projected_final_views = smoothed_points[-1]["velocity"] * 1440 if smoothed_points and smoothed_points[-1]["velocity"] else 0 # 24hr rough projection
    
    payload = {
        "reel_id": active_id,
        "current_trajectory": smoothed_points,
        "24h_predicted_views": projected_final_views,
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
