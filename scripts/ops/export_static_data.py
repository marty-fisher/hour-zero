import argparse
import os
import json
import psycopg2
from dotenv import load_dotenv

def export_active_reel(output_path):
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
    db_url = os.getenv('SUPABASE_DB_URL')
    
    if not db_url:
        print("Error: SUPABASE_DB_URL not found in .env")
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
        SELECT age_minutes, velocity, relative_velocity
        FROM public.poll_metrics
        WHERE reel_id = %s
        ORDER BY polled_at ASC;
    """
    cur.execute(query, (active_id,))
    rows = cur.fetchall()
    
    # Build payload with mock/DTW projections
    points = [{"age_minutes": r[0], "velocity": r[1], "relative_velocity": r[2]} for r in rows]
    
    # Simple projection (Archetype Shape matching placeholder)
    projected_final_views = points[-1]["velocity"] * 1440 if points and points[-1]["velocity"] else 0 # 24hr rough projection
    
    payload = {
        "reel_id": active_id,
        "current_trajectory": points,
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
