"""
Refreshes topic_rollups by recomputing counts for the last 3 days.

Unlike normaliser.py / classify_pending.py (which process a growing
backlog), this script re-derives a small, bounded window every run and
upserts it — so re-running it is always safe, and it naturally picks up
items that were classified late (e.g. a comment scraped today that
belongs to a 2-day-old post).

The Supabase REST client can't do a SQL JOIN directly, so this fetches
content_items and content_item_topics separately, joins them in Python
with a dict, then groups and counts — same "fetch, process in Python,
write back" shape as the rest of this pipeline, just no LLM/model call
this time, purely arithmetic.
"""

import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

WINDOW_DAYS = 3


def fetch_recent_content_items():
    """id, source_type, and posted_at for everything in the rolling window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)).isoformat()
    result = (
        supabase.table("content_items")
        .select("id,source_type,posted_at")
        .gte("posted_at", cutoff)
        .execute()
    )
    return result.data


def fetch_topics_for_items(content_item_ids):
    """topic per content_item_id, only for the ids we actually need."""
    if not content_item_ids:
        return {}
    result = (
        supabase.table("content_item_topics")
        .select("content_item_id,topic")
        .in_("content_item_id", content_item_ids)
        .execute()
    )
    # one item -> one topic in v1 (no secondary labels yet), so a plain dict is fine
    return {row["content_item_id"]: row["topic"] for row in result.data}


def to_bucket_date(posted_at_str):
    """posted_at comes back as an ISO timestamp string — we only need the date part."""
    return datetime.fromisoformat(posted_at_str).date().isoformat()


def compute_rollups():
    items = fetch_recent_content_items()
    print(f"Fetched {len(items)} content_items from the last {WINDOW_DAYS} days")

    topics_by_item_id = fetch_topics_for_items([item["id"] for item in items])

    # counts[(topic, source_type, bucket_date)] = count
    counts = defaultdict(int)
    skipped_no_topic = 0

    for item in items:
        topic = topics_by_item_id.get(item["id"])
        if topic is None:
            skipped_no_topic += 1
            continue  # not yet classified — will be picked up once classify_pending.py runs
        bucket_date = to_bucket_date(item["posted_at"])
        counts[(topic, item["source_type"], bucket_date)] += 1

    if skipped_no_topic:
        print(f"  {skipped_no_topic} recent items have no topic yet (not classified)")

    return counts


def upsert_rollups(counts):
    if not counts:
        print("Nothing to upsert.")
        return

    payload = [
        {"topic": topic, "source_type": source_type, "bucket_date": bucket_date, "item_count": count}
        for (topic, source_type, bucket_date), count in counts.items()
    ]

    # on_conflict targets the UNIQUE (topic, source_type, bucket_date) constraint —
    # this is what makes re-running the script safe: an existing (topic, source,
    # date) row gets its count REPLACED with the fresh total, not duplicated.
    supabase.table("topic_rollups").upsert(
        payload, on_conflict="topic,source_type,bucket_date"
    ).execute()

    print(f"Upserted {len(payload)} (topic, source, date) rows into topic_rollups")


def main():
    counts = compute_rollups()
    upsert_rollups(counts)


if __name__ == "__main__":
    main()