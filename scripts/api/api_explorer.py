import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
IG_ACCOUNT_ID = os.getenv("ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("TOKEN")


def explore_api():
    if not IG_ACCOUNT_ID or not ACCESS_TOKEN:
        print("Error: Missing credentials in .env")
        return

    print("Fetching the latest Reel to dissect available fields...\n")

    url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"

    # We are throwing the kitchen sink at the API.
    # 1. Top-level fields (like_count, comments_count, play_count)
    # 2. Every possible video-related insight metric
    params = {
        "fields": "id,media_type,media_product_type,like_count,comments_count,play_count,views_count,insights.metric(plays,video_views,reach,saved,shares,total_interactions)",
        "access_token": ACCESS_TOKEN,
        "limit": 1,
    }

    try:
        response = requests.get(url, params=params)

        # If Meta gets mad at one of our requested metrics, it will throw a 400.
        # We want to see that exact error, so we print the raw text if it fails.
        if response.status_code != 200:
            print(f"API REJECTED THE REQUEST. Status: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
            return

        data = response.json()
        latest_media = data.get("data", [])[0]

        print("===" * 15)
        print("RAW JSON RESPONSE:")
        print("===" * 15)
        print(json.dumps(latest_media, indent=2))
        print("\n" + "===" * 15)

        # Let's do a quick diagnostic check
        print("DIAGNOSTIC REPORT:")
        print(f"Media Type:         {latest_media.get('media_type')}")
        print(f"Product Type:       {latest_media.get('media_product_type')}")

        # Check top level fields
        play_count = latest_media.get("play_count", "NOT FOUND")
        print(f"Top-Level Plays:    {play_count}")

        # Check insights
        insights = latest_media.get("insights", {}).get("data", [])
        insight_names = [metric.get("name") for metric in insights]
        print(
            f"Available Insights: {', '.join(insight_names) if insight_names else 'NONE'}"
        )
        print("===" * 15)

    except Exception as e:
        print(f"Script Error: {e}")


if __name__ == "__main__":
    explore_api()
