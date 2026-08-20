import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 500


def _news_text(row):
    return f"{row.get('title') or ''}\n\n{row.get('body') or ''}".strip()


def _paper_text(row):
    return f"{row.get('title') or ''}\n\n{row.get('body') or ''}".strip()


def _reddit_post_text(row):
    return f"{row.get('title') or ''}\n\n{row.get('body') or ''}".strip()


def _reddit_comment_text(row):
    return (row.get("body") or "").strip()


def _device_text(row):
    # key_takeaways is stored as a stringified JSON array — parse before joining
    takeaways_raw = row.get("key_takeaways")
    takeaways = ""
    if takeaways_raw:
        try:
            items = json.loads(takeaways_raw)
            takeaways = "\n".join(items) if isinstance(items, list) else str(items)
        except (json.JSONDecodeError, TypeError):
            takeaways = takeaways_raw  # fall back to raw string if it's not JSON
    return f"{row.get('title') or ''}\n\n{takeaways}\n\n{row.get('body') or ''}".strip()


def _podcast_text(row):
    return f"{row.get('title') or ''}\n\n{row.get('transcript') or ''}".strip()


# One entry per source table. Add new sources here — nothing else needs to change.
NORMALIZE_CONFIGS = [
    {
        "table": "reddit_posts",
        "id_col": "post_id",
        "source_type": "reddit_post",
        "posted_at_col": "created_at",
        "text_fn": _reddit_post_text,
        "extra_filter": None,
    },
    {
        "table": "reddit_post_comments",
        "id_col": "comment_id",
        "source_type": "reddit_comment",
        "posted_at_col": "created_at",
        "text_fn": _reddit_comment_text,
        "extra_filter": None,
    },
    {
        "table": "news_db",
        "id_col": "url",
        "source_type": "news",
        "posted_at_col": "created_at",
        "text_fn": _news_text,
        "extra_filter": None,
    },
    {
        "table": "mdpi_papers",
        "id_col": "url",
        "source_type": "paper",
        "posted_at_col": "published_at",
        "text_fn": _paper_text,
        "extra_filter": None,
    },
    {
        "table": "energybased_devices",
        "id_col": "url",
        "source_type": "device",
        "posted_at_col": "published_at",
        "text_fn": _device_text,
        "extra_filter": None,
    },
    {
        "table": "Amspa_podcasts",
        "id_col": "video_id",
        "source_type": "podcast",
        "posted_at_col": "published_date",
        "text_fn": _podcast_text,
        # skip rows with no transcript (e.g. junk/test rows) rather than
        # normalizing empty content
        "extra_filter": lambda q: q.not_.is_("transcript", "null"),
    },
]


def normalize_table(config):
    """Normalize every is_normalised=false row for a single source table."""
    table = config["table"]
    id_col = config["id_col"]
    source_type = config["source_type"]
    posted_at_col = config["posted_at_col"]
    text_fn = config["text_fn"]
    extra_filter = config["extra_filter"]

    total_processed = 0

    while True:
        query = supabase.table(table).select("*").eq("is_normalised", False).limit(BATCH_SIZE)
        if extra_filter:
            query = extra_filter(query)
        result = query.execute()
        rows = result.data

        if not rows:
            break

        payload = []
        row_ids = []
        for row in rows:
            text = text_fn(row)
            if not text:
                # nothing usable to embed — mark normalised so it doesn't loop forever,
                # but don't create an empty content_items row
                row_ids.append(row[id_col])
                continue
            payload.append({
                "source_type": source_type,
                "source_id": row[id_col],
                "text_for_embedding": text,
                "posted_at": row[posted_at_col],
            })
            row_ids.append(row[id_col])

        if payload:
            try:
                supabase.table("content_items").upsert(
                    payload, on_conflict="source_type,source_id"
                ).execute()
            except Exception as e:
                print(f"  ERROR upserting batch for {table}: {e}")
                print(f"  Skipping flag update for this batch — will retry on next run.")
                continue  # don't mark these as normalised if the insert failed

        supabase.table(table).update({"is_normalised": True}).in_(id_col, row_ids).execute()
        total_processed += len(row_ids)
        print(f"  {table}: normalised {len(row_ids)} rows (running total: {total_processed})")

    if total_processed == 0:
        print(f"  {table}: nothing pending, already up to date.")

    return total_processed


def main():
    print("Running normalization catch-up across all source tables...\n")
    grand_total = 0
    for config in NORMALIZE_CONFIGS:
        print(f"Processing {config['table']}...")
        grand_total += normalize_table(config)
    print(f"\nDone. {grand_total} total rows normalised into content_items.")


if __name__ == "__main__":
    main()