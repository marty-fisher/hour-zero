import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
IG_ACCOUNT_ID = os.getenv("ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("TOKEN")

url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media"
params = {
    "fields": "id,media_type,timestamp,insights.metric(views,reach,likes,comments,shares,saved)",
    "access_token": ACCESS_TOKEN,
    "limit": 1,
}

print("Pinging Meta API...")
response = requests.get(url, params=params)

print(f"HTTP Status: {response.status_code}")
print("META ERROR PAYLOAD:")
print(json.dumps(response.json(), indent=2))
