import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 500
PARENT_COMMENT_SNIPPET_LEN = 100  


def _news_text(row, context=None):
    return f"{row.get('title') or ''}\n\n{row.get('body') or ''}".strip()


def _paper_text(row, context=None):
    return f"{row.get('title') or ''}\n\n{row.get('body') or ''}".strip()


def _reddit_post_text(row, context=None):
    return f"{row.get('title') or ''}\n\n{row.get('body') or ''}".strip()


def _reddit_comment_context(rows, sb):
    """
    One bulk fetch per batch (not per row) to get:
      - the parent post's title, for every comment in this batch
      - the parent comment's body, for comments that are replies to another comment
    """
    post_ids = list({r["post_id"] for r in rows if r.get("post_id")})
    parent_comment_ids = list({r["parent_comment_id"] for r in rows if r.get("parent_comment_id")})

    post_title_by_id = {}
    if post_ids:
        res = sb.table("reddit_posts").select("post_id,title").in_("post_id", post_ids).execute()
        post_title_by_id = {r["post_id"]: r["title"] for r in res.data}

    parent_body_by_id = {}
    if parent_comment_ids:
        res = (
            sb.table("reddit_post_comments")
            .select("comment_id,body")
            .in_("comment_id", parent_comment_ids)
            .execute()
        )
        parent_body_by_id = {r["comment_id"]: r["body"] for r in res.data}

    return {"post_title_by_id": post_title_by_id, "parent_body_by_id": parent_body_by_id}


def _reddit_comment_text(row, context=None):
    context = context or {}
    body = (row.get("body") or "").strip()

    post_title = context.get("post_title_by_id", {}).get(row.get("post_id"), "")

    parent_snippet = ""
    parent_comment_id = row.get("parent_comment_id")
    if parent_comment_id:
        parent_body = context.get("parent_body_by_id", {}).get(parent_comment_id)
        if parent_body:
            trimmed = parent_body.strip()[:PARENT_COMMENT_SNIPPET_LEN]
            parent_snippet = f" > replying to: {trimmed}"

    if not post_title:
        # fallback — shouldn't normally happen, but don't lose the comment if the join misses
        return body

    return f"[Context: {post_title}{parent_snippet}] {body}".strip()


def _device_text(row, context=None):
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


def _podcast_text(row, context=None):
    return f"{row.get('title') or ''}\n\n{row.get('transcript') or ''}".strip()


# One entry per source table. Add new sources here — nothing else needs to change.
NORMALIZE_CONFIGS = [
    {
        "table": "reddit_posts",
        "id_col": "post_id",
        "source_type": "reddit_post",
        "posted_at_col": "created_at",
        "text_fn": _reddit_post_text,
        "context_fn": None,
        "extra_filter": None,
    },
    {
        "table": "reddit_post_comments",
        "id_col": "comment_id",
        "source_type": "reddit_comment",
        "posted_at_col": "created_at",
        "text_fn": _reddit_comment_text,
        "context_fn": _reddit_comment_context,  # bulk-fetches post titles + parent comment snippets
        "extra_filter": None,
    },
    {
        "table": "news_db",
        "id_col": "url",
        "source_type": "news",
        "posted_at_col": "created_at",
        "text_fn": _news_text,
        "context_fn": None,
        "extra_filter": None,
    },
    {
        "table": "mdpi_papers",
        "id_col": "url",
        "source_type": "paper",
        "posted_at_col": "published_at",
        "text_fn": _paper_text,
        "context_fn": None,
        "extra_filter": None,
    },
    {
        "table": "energybased_devices",
        "id_col": "url",
        "source_type": "device",
        "posted_at_col": "published_at",
        "text_fn": _device_text,
        "context_fn": None,
        "extra_filter": None,
    },
    {
        "table": "Amspa_podcasts",
        "id_col": "video_id",
        "source_type": "podcast",
        "posted_at_col": "published_date",
        "text_fn": _podcast_text,
        "context_fn": None,
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
    context_fn = config.get("context_fn")
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

        # one bulk lookup for the whole batch, not one query per row
        context = context_fn(rows, supabase) if context_fn else None

        payload = []
        row_ids = []
        for row in rows:
            text = text_fn(row, context)
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