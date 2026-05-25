import os
import base64
import json
import re

import functions_framework
import psycopg2
import requests
from datetime import datetime, timezone, timedelta

# Configuration from environment variables
INSTAGRAM_ACCOUNT_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID")
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL")
GRAPH_API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Adaptive polling tiers: (max_age_seconds, tier_name, min_gap_seconds)
POLL_TIERS = [
    (24 * 60 * 60, "fast", 50),  # 0-24h: ~1 min cadence for maximum data resolution
]


def get_db():
    """Get a psycopg2 connection to Supabase Postgres."""
    return psycopg2.connect(SUPABASE_DB_URL)


def get_age_tier(age_seconds: int) -> tuple[str, int]:
    """Returns (tier_name, min_seconds_between_polls) for the given reel age."""
    for max_age, tier, gap in POLL_TIERS:
        if age_seconds < max_age:
            return (tier, gap)
    return ("expired", -1)


# =============================================================================
# ENTRY POINTS
# =============================================================================


@functions_framework.http
def ingest_metrics(request):
    """HTTP entry point (Cloud Scheduler heartbeat, every 1 min)."""
    return run_ingestion_cycle()


@functions_framework.http
def detect_new_reel(request):
    """
    Fallback new-reel detector (Cloud Scheduler, every 10 min).

    Polls Meta for the latest media and checks if it's a new VIDEO
    within the 24h window that we aren't already tracking. If found,
    activates tracking -- acts as a safety net in case the webhook misses.
    """
    if not INSTAGRAM_ACCOUNT_ID or not META_ACCESS_TOKEN:
        return "Missing configuration", 500
    if not SUPABASE_DB_URL:
        return "Missing SUPABASE_DB_URL", 500

    try:
        latest = get_latest_media()
        if not latest or latest.get("media_type") != "VIDEO":
            return "No recent VIDEO found", 200

        media_id = latest["id"]
        posted_at = parse_meta_timestamp(latest["timestamp"])
        now = datetime.now(timezone.utc)
        age = now - posted_at

        # Only care about reels less than 24h old
        if age > timedelta(hours=24):
            return "Latest reel is older than 24h", 200

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT active_reel_id FROM tracking_state WHERE id = 1")
                row = cur.fetchone()
                current_active = row[0] if row else None

                if current_active == media_id:
                    return f"Already tracking {media_id}", 200

                # New reel detected -- activate it
                print(
                    f"FALLBACK DETECT: New reel {media_id} found, activating tracking"
                )
                expires_at = posted_at + timedelta(hours=24)
                cur.execute(
                    """
                    UPDATE tracking_state
                    SET active_reel_id = %s, expires_at = %s, last_polled = NULL
                    WHERE id = 1
                    """,
                    (media_id, expires_at),
                )
                conn.commit()

            # Immediately do a first poll
            return run_ingestion_cycle(force_reel_id=media_id)
        finally:
            conn.close()

    except Exception as e:
        print(f"Fallback detect error: {e!s}")
        return f"Error: {e!s}", 500


@functions_framework.cloud_event
def pubsub_ingest(cloud_event):
    """Pub/Sub entry point (instant Webhook trigger)."""
    media_id = None
    try:
        data = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        trigger_info = json.loads(data)
        print(f"Instant Trigger Received: {trigger_info}")

        media_id = trigger_info.get("target_id")
        if not media_id:
            webhook_data = trigger_info.get("data", {})
            raw_id = webhook_data.get("id")
            if raw_id:
                media_id = raw_id.split("_")[-1]

    except Exception as e:
        print(f"Error parsing Pub/Sub message: {e}")

    return run_ingestion_cycle(force_reel_id=media_id)


# =============================================================================
# CORE LOGIC
# =============================================================================


def run_ingestion_cycle(force_reel_id=None):
    """Core ingestion logic shared by both triggers."""
    if not INSTAGRAM_ACCOUNT_ID or not META_ACCESS_TOKEN:
        return "Missing configuration", 500
    if not SUPABASE_DB_URL:
        return "Missing SUPABASE_DB_URL", 500

    conn = get_db()
    now = datetime.now(timezone.utc)

    try:
        with conn.cursor() as cur:
            if force_reel_id:
                # Webhook path: activate this reel for tracking if new, or process immediately
                media_id = force_reel_id
                media_info = get_media_info(media_id)
                if not media_info:
                    return f"Could not find media {media_id}", 404
                    
                cur.execute(
                    "SELECT active_reel_id, expires_at, last_polled FROM tracking_state WHERE id = 1"
                )
                row = cur.fetchone()
                current_active = row[0] if row else None
                last_polled = row[2] if row else None

                posted_at = parse_meta_timestamp(media_info["timestamp"])
                expires_at = posted_at + timedelta(hours=24)
                
                # Check rate limits even on webhooks!
                if current_active == media_id and last_polled:
                    age_seconds = (now - posted_at).total_seconds()
                    tier, min_gap = get_age_tier(int(age_seconds))
                    if (now - last_polled).total_seconds() < min_gap:
                        return f"Skipped webhook force poll (tier={tier}, too soon, {min_gap}s gap required)", 200

                cur.execute(
                    """
                    UPDATE tracking_state
                    SET active_reel_id = %s, expires_at = %s, last_polled = %s
                    WHERE id = 1
                    """,
                    (media_id, expires_at, now),
                )
                conn.commit()
            else:
                # Heartbeat path: check if we have an active reel
                cur.execute(
                    "SELECT active_reel_id, expires_at, last_polled FROM tracking_state WHERE id = 1"
                )
                row = cur.fetchone()
                if not row or not row[0]:
                    return "No active Reel tracking in progress.", 200

                media_id, expires_at, last_polled = row

                # Check TTL
                if expires_at and now > expires_at:
                    cur.execute(
                        "UPDATE tracking_state SET active_reel_id = NULL WHERE id = 1"
                    )
                    conn.commit()
                    return "Tracking period expired. Clearing state.", 200

                # Adaptive cadence: check if enough time has passed
                media_info = get_media_info(media_id)
                if media_info:
                    posted_at = parse_meta_timestamp(media_info["timestamp"])
                    age_seconds = (now - posted_at).total_seconds()
                    tier, min_gap = get_age_tier(int(age_seconds))

                    if tier == "expired":
                        cur.execute(
                            "UPDATE tracking_state SET active_reel_id = NULL WHERE id = 1"
                        )
                        conn.commit()
                        return "Tracking period expired.", 200

                    if last_polled and (now - last_polled).total_seconds() < min_gap:
                        return f"Skipped (tier={tier}, too soon)", 200

        # Process the media
        if not media_info or media_info.get("media_type") != "VIDEO":
            return "Media not found or not a Reel", 200

        metrics = fetch_insights(media_id)
        if not metrics:
            return f"Failed to fetch metrics for {media_id}", 500

        posted_at = parse_meta_timestamp(media_info["timestamp"])
        age_seconds = int((now - posted_at).total_seconds())
        tier, _ = get_age_tier(age_seconds)

        # Determine source
        source = "webhook" if force_reel_id else "scheduled"

        # Write to Postgres
        write_to_postgres(conn, media_info, metrics, now, tier, source)

        # Update last polled
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE tracking_state SET last_polled = %s WHERE id = 1", (now,)
            )
        conn.commit()

        return f"Successfully processed Reel {media_id} (tier={tier})", 200

    except Exception as e:
        print(f"Error: {e!s}")
        conn.rollback()
        return f"Internal Error: {e!s}", 500
    finally:
        conn.close()


# =============================================================================
# META API
# =============================================================================


def get_media_info(media_id):
    """Fetch specific media info by ID from Meta Graph API."""
    url = f"{BASE_URL}/{media_id}"
    params = {
        "fields": "id,caption,media_type,permalink,timestamp",
        "access_token": META_ACCESS_TOKEN,
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None
    return response.json()


def get_latest_media():
    """Query Meta Graph API for the single most recent media object."""
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"
    params = {
        "fields": "id,caption,media_type,permalink,timestamp",
        "limit": 1,
        "access_token": META_ACCESS_TOKEN,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json().get("data", [])
    return data[0] if data else None


def fetch_insights(media_id):
    """Fetch insights for a specific media object."""
    url = f"{BASE_URL}/{media_id}/insights"
    metrics_list = "views,reach,likes,comments,shares,saved"
    params = {"metric": metrics_list, "access_token": META_ACCESS_TOKEN}
    response = requests.get(url, params=params)
    response.raise_for_status()

    raw_data = response.json().get("data", [])
    parsed_metrics = {}
    for entry in raw_data:
        name = entry.get("name")
        value = entry.get("values", [{}])[0].get("value", 0)
        parsed_metrics[name] = value

    return parsed_metrics


def fetch_follower_count():
    """Fetch current follower count for the Instagram account."""
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}"
    params = {
        "fields": "followers_count",
        "access_token": META_ACCESS_TOKEN,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("followers_count")
    except Exception as e:
        print(f"Warning: Could not fetch follower count: {e}")
        return None


def check_ttl(posted_at_str):
    """Check if the media is within the 24-hour tracking window."""
    posted_at = parse_meta_timestamp(posted_at_str)
    now = datetime.now(timezone.utc)
    age = now - posted_at
    return age <= timedelta(hours=24)


# =============================================================================
# DATABASE WRITES
# =============================================================================


def write_to_postgres(conn, media_info, metrics, now, tier, source):
    """Persist reel + poll data to Supabase Postgres."""
    reel_id = media_info["id"]
    posted_at = parse_meta_timestamp(media_info["timestamp"])
    caption = media_info.get("caption", "")

    with conn.cursor() as cur:
        # Check if reel already exists
        cur.execute("SELECT id FROM reels WHERE id = %s", (reel_id,))
        is_new_reel = cur.fetchone() is None

        # Upsert reel
        follower_count = fetch_follower_count() if is_new_reel else None
        hashtag_count = len(re.findall(r"#\w+", caption)) if caption else 0

        if is_new_reel:
            cur.execute(
                """
                INSERT INTO reels (id, url, caption, posted_at, follower_count_at_post, hashtag_count)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    reel_id,
                    media_info.get("permalink"),
                    caption,
                    posted_at,
                    follower_count,
                    hashtag_count,
                ),
            )
        else:
            cur.execute(
                """
                UPDATE reels SET url = %s, caption = %s WHERE id = %s
                """,
                (media_info.get("permalink"), caption, reel_id),
            )

        # Insert poll
        cur.execute(
            """
            INSERT INTO polls (reel_id, polled_at, views, reach, likes, comments, shares, saved,
                               poll_cadence_tier, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (reel_id, polled_at) DO NOTHING
            """,
            (
                reel_id,
                now,
                metrics.get("views", 0),
                metrics.get("reach"),
                metrics.get("likes"),
                metrics.get("comments"),
                metrics.get("shares"),
                metrics.get("saved"),
                tier,
                source,
            ),
        )

    conn.commit()


# =============================================================================
# HELPERS
# =============================================================================


def parse_meta_timestamp(ts_str):
    """Parse Meta's ISO 8601 timestamp format into a timezone-aware datetime."""
    return datetime.fromisoformat(ts_str.replace("+0000", "+00:00"))
