"""
Bootstrap labeling script for the topic taxonomy.

Pulls a stratified sample of 700 content_items (all of the small sources,
a random slice of reddit_comment to fill the rest), sends each one to
Groq (Llama 3.3 70B Versatile) with the fixed 11-category taxonomy, and
writes results to a LOCAL CSV — nothing is written back to Supabase here.
Review the CSV for label quality before using it to train the classifier.

Env vars needed: SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY
"""

import os
import csv
import json
import time
from dotenv import load_dotenv
from supabase import create_client
from groq import Groq

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Verify this against Groq's current model list before running —
# model names/versions get deprecated and replaced over time.
GROQ_MODEL = "openai/gpt-oss-120b"

OUTPUT_CSV = "bootstrap_labels.csv"
REQUEST_DELAY_SECONDS = 5  # be polite to the rate limit; adjust if needed

TAXONOMY = [
    "Injectables & Fillers",
    "GLP-1, Weight Loss & Peptides",
    "Body Contouring & Energy-Based Devices",
    "Regulatory & Legal",
    "Safety Incidents",
    "Business Operations & Marketing",
    "Product & Device Launches",
    "Consumer Experiences & Complaints",
    "Career & Training",
    "Research & Clinical Findings",
    "Off-topic / Not relevant",
]

SYSTEM_PROMPT = f"""You are labeling content for a market-intelligence system covering the \
aesthetic clinic / med spa industry. Given a piece of text, assign it to ONE primary category \
from this fixed list, and OPTIONALLY a second category if the content genuinely spans two \
distinct topics (e.g. a device complaint that is also a consumer complaint).

Categories:
{chr(10).join(f"- {c}" for c in TAXONOMY)}

Rules:
- "Off-topic / Not relevant" is for content that mentions industry keywords only incidentally \
(e.g. a garage sale post, a TV show recap, a general career/job post unrelated to aesthetics) \
and is not actually about the industry.
- Only use a secondary category if it's genuinely a second, distinct topic — most items need \
only a primary category.
- Respond with ONLY valid JSON, no other text: {{"primary": "<category>", "secondary": "<category or null>"}}
"""


def fetch_stratified_sample():
    """Pull all rows from small sources, a random slice of reddit_comment to reach 700 total."""
    rows = []

    full_sources = ["device", "podcast", "paper", "news", "reddit_post"]
    for source_type in full_sources:
        result = (
            supabase.table("content_items")
            .select("id,source_type,text_for_embedding")
            .eq("source_type", source_type)
            .execute()
        )
        rows.extend(result.data)
        print(f"  {source_type}: pulled {len(result.data)} rows")

    remaining_budget = 700 - len(rows)
    print(f"  reddit_comment: sampling {remaining_budget} rows to fill the remainder")

    # Supabase doesn't have a native ORDER BY random() through the client library,
    # so pull a larger batch and sample client-side.
    comment_pool = (
        supabase.table("content_items")
        .select("id,source_type,text_for_embedding")
        .eq("source_type", "reddit_comment")
        .limit(2000)
        .execute()
    )
    import random
    sampled_comments = random.sample(comment_pool.data, min(remaining_budget, len(comment_pool.data)))
    rows.extend(sampled_comments)

    print(f"  Total sample size: {len(rows)}")
    return rows


def label_item(text):
    """Call Groq once for a single item, return (primary, secondary) or (None, None) on failure."""
    truncated_text = text[:2000]  # keep prompt size sane for very long papers
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": truncated_text},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        primary = parsed.get("primary")
        secondary = parsed.get("secondary")
        if primary not in TAXONOMY:
            print(f"    WARNING: model returned unknown primary category: {primary!r}")
            return None, None
        if secondary is not None and secondary not in TAXONOMY:
            secondary = None  # drop invalid secondary rather than failing the whole row
        return primary, secondary
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        print(f"    ERROR parsing model response: {e}")
        return None, None
    except Exception as e:
        print(f"    ERROR calling Groq: {e}")
        return None, None


def main():
    print("Fetching stratified sample...")
    rows = fetch_stratified_sample()

    print(f"\nLabeling {len(rows)} items via Groq ({GROQ_MODEL})...")
    print(f"Writing results to {OUTPUT_CSV} as they come in — safe to interrupt and resume later.\n")

    already_labeled_ids = set()
    file_exists = os.path.exists(OUTPUT_CSV)
    if file_exists:
        with open(OUTPUT_CSV, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                already_labeled_ids.add(int(row["content_item_id"]))
        print(f"Resuming: {len(already_labeled_ids)} items already labeled in existing CSV.\n")

    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["content_item_id", "source_type", "text_preview", "primary_topic", "secondary_topic"])

        success_count = 0
        failure_count = 0

        for i, row in enumerate(rows, 1):
            if row["id"] in already_labeled_ids:
                continue

            primary, secondary = label_item(row["text_for_embedding"])

            if primary is None:
                failure_count += 1
                print(f"  [{i}/{len(rows)}] SKIPPED (labeling failed) — id {row['id']}")
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            preview = row["text_for_embedding"][:100].replace("\n", " ")
            writer.writerow([row["id"], row["source_type"], preview, primary, secondary or ""])
            f.flush()  # write immediately so progress isn't lost on interruption

            success_count += 1
            if i % 50 == 0:
                print(f"  [{i}/{len(rows)}] labeled so far: {success_count} ok, {failure_count} failed")

            time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\nDone. {success_count} labeled, {failure_count} failed. Review {OUTPUT_CSV} before training.")


if __name__ == "__main__":
    main()