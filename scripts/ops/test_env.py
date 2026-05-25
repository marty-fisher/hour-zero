import os
import requests
import psycopg2
from dotenv import load_dotenv
import json

def test_meta_api():
    print("Testing Meta API connection...")
    IG_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
    ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
    
    if not IG_ACCOUNT_ID or not ACCESS_TOKEN:
        print("❌ Missing Meta credentials in .env")
        return False
        
    url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
    params = {
        "fields": "id,media_type,timestamp,insights.metric(views,reach,likes,comments,shares,saved)",
        "access_token": ACCESS_TOKEN,
        "limit": 1,
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"HTTP Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Meta API Connection Successful!")
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                print(f"Sample data retrieved: {data['data'][0]['id']}")
            return True
        else:
            print("❌ Meta API Error:")
            print(json.dumps(response.json(), indent=2))
            return False
    except Exception as e:
        print(f"❌ Exception during Meta API call: {e}")
        return False

def test_supabase_db():
    print("\nTesting Supabase Database connection...")
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
    
    if not SUPABASE_DB_URL:
        print("❌ Missing SUPABASE_DB_URL in .env")
        return False
        
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        result = cur.fetchone()
        if result and result[0] == 1:
            print("✅ Supabase DB Connection Successful!")
            
            # Let's check some table counts
            cur.execute("SELECT count(*) FROM reels;")
            reels_count = cur.fetchone()[0]
            print(f"Total Reels tracked: {reels_count}")
            
            cur.execute("SELECT count(*) FROM polls;")
            polls_count = cur.fetchone()[0]
            print(f"Total Polls recorded: {polls_count}")
            
            # Let's check if the view works
            cur.execute("SELECT count(*) FROM poll_metrics_enriched;")
            views_count = cur.fetchone()[0]
            print(f"Total Enriched Poll Metrics (view check): {views_count}")
            
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"❌ Exception during DB connection: {e}")
        return False

if __name__ == "__main__":
    load_dotenv()
    test_meta_api()
    test_supabase_db()
