import os
import psycopg2
from dotenv import load_dotenv
import json
from datetime import datetime

def check_recent_entries():
    load_dotenv()
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
    
    if not SUPABASE_DB_URL:
        print("❌ Missing SUPABASE_DB_URL in .env")
        return
        
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cur = conn.cursor()
        
        print("--- Most Recent Reels ---")
        cur.execute("SELECT id, posted_at, created_at FROM reels ORDER BY created_at DESC LIMIT 5;")
        reels = cur.fetchall()
        for r in reels:
            print(f"ID: {r[0]}, Posted: {r[1]}, Tracked At: {r[2]}")
            
        print("\n--- Most Recent Polls ---")
        cur.execute("SELECT reel_id, polled_at, views, reach FROM polls ORDER BY polled_at DESC LIMIT 5;")
        polls = cur.fetchall()
        for p in polls:
            print(f"Reel ID: {p[0]}, Polled At: {p[1]}, Views: {p[2]}, Reach: {p[3]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Exception during DB query: {e}")

if __name__ == "__main__":
    check_recent_entries()
