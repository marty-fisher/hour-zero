import os
import requests
from dotenv import load_dotenv
from google.cloud import firestore
from datetime import datetime, timezone

load_dotenv()
IG_ACCOUNT_ID = os.getenv("ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("TOKEN")
PROJECT_ID = os.getenv("PROJECT_ID")

if not PROJECT_ID:
    print("Error: Missing PROJECT_ID in .env")
    exit()

db = firestore.Client(project=PROJECT_ID)


def backfill_historical_reels():
    if not IG_ACCOUNT_ID or not ACCESS_TOKEN:
        print("Error: Missing ACCOUNT_ID or TOKEN in .env")
        return

    print(f"Starting historical data backfill for project: {PROJECT_ID}...")

    url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"

    # Swapped 'plays' for 'views' and added 'reach'
    params = {
        "fields": "id,caption,media_type,timestamp,permalink,insights.metric(views,reach,likes,comments,shares,saved)",
        "access_token": ACCESS_TOKEN,
        "limit": 25,
    }

    current_url = url
    current_params = params
    total_processed = 0

    while current_url:
        print("Fetching a batch of posts...")
        response = requests.get(current_url, params=current_params)

        if response.status_code != 200:
            print(f"API Error: {response.text}")
            break

        data = response.json()
        posts = data.get("data", [])

        for item in posts:
            if item.get("media_type") == "VIDEO":
                reel_id = item.get("id")
                posted_at = item.get("timestamp")
                permalink = item.get("permalink")
                caption = item.get("caption", "")

                metrics = {}
                insights = item.get("insights", {}).get("data", [])
                for metric in insights:
                    name = metric.get("name")
                    value = metric.get("values", [{}])[0].get("value", 0)
                    metrics[name] = value

                reel_ref = db.collection("reels").document(reel_id)
                reel_ref.set(
                    {
                        "url": permalink,
                        "posted_at": posted_at,
                        "caption": caption,
                        "is_historical_backfill": True,
                    },
                    merge=True,
                )

                poll_data = {
                    "timestamp_polled": datetime.now(timezone.utc),
                    "metrics": metrics,
                    "note": "Historical Baseline",
                }
                reel_ref.collection("polls").add(poll_data)

                total_processed += 1
                print(
                    f"  -> Logged historical data for Reel: {reel_id} ({metrics.get('views', 0)} views)"
                )

        paging = data.get("paging", {})
        next_page = paging.get("next")

        if next_page:
            current_url = next_page
            current_params = None
        else:
            current_url = None

    print(
        f"\nBackfill Complete! Successfully processed {total_processed} historical Reels."
    )


if __name__ == "__main__":
    backfill_historical_reels()
