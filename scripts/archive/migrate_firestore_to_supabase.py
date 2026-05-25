"""
One-time migration script: Firestore -> Supabase Postgres.

Reads all reels and their polls from Firestore and inserts them into
the Supabase Postgres database. Idempotent (ON CONFLICT DO NOTHING).

Usage:
    python scripts/migrate_firestore_to_supabase.py
"""

import os

import psycopg2
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")


def migrate():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL not set in .env")
        return

    if not PROJECT_ID:
        print("Error: GOOGLE_CLOUD_PROJECT / PROJECT_ID not set in .env")
        return

    print(f"Connecting to Firestore (project: {PROJECT_ID})...")
    fs = firestore.Client(project=PROJECT_ID)

    print("Connecting to Supabase Postgres...")
    conn = psycopg2.connect(SUPABASE_DB_URL)

    reels_ref = fs.collection("reels")
    reel_docs = list(reels_ref.stream())
    print(f"Found {len(reel_docs)} reels in Firestore.")

    total_polls = 0

    with conn.cursor() as cur:
        for reel_doc in reel_docs:
            reel_data = reel_doc.to_dict()
            reel_id = reel_doc.id

            posted_at = reel_data.get("posted_at")
            if not posted_at:
                print(f"  Skipping reel {reel_id}: no posted_at")
                continue

            # Insert reel
            cur.execute(
                """
                INSERT INTO reels (id, url, caption, posted_at, is_historical_backfill)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    reel_id,
                    reel_data.get("url"),
                    reel_data.get("caption", ""),
                    posted_at,
                    reel_data.get("is_historical_backfill", False),
                ),
            )

            # Migrate polls
            polls_ref = reels_ref.document(reel_id).collection("polls")
            polls = list(polls_ref.order_by("timestamp_polled").stream())

            for poll_doc in polls:
                poll_data = poll_doc.to_dict()
                metrics = poll_data.get("metrics", {})
                polled_at = poll_data.get("timestamp_polled")

                if not polled_at:
                    continue

                cur.execute(
                    """
                    INSERT INTO polls (reel_id, polled_at, views, reach, likes, comments,
                                       shares, saved, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (reel_id, polled_at) DO NOTHING
                    """,
                    (
                        reel_id,
                        polled_at,
                        metrics.get("views", 0),
                        metrics.get("reach"),
                        metrics.get("likes"),
                        metrics.get("comments"),
                        metrics.get("shares"),
                        metrics.get("saved"),
                        "backfill",
                    ),
                )
                total_polls += 1

            print(f"  Migrated reel {reel_id} ({len(polls)} polls)")

    conn.commit()
    conn.close()
    print(f"\nMigration complete: {len(reel_docs)} reels, {total_polls} polls.")


if __name__ == "__main__":
    migrate()
