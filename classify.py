"""
Uses the trained topic_classifier.joblib to tag every content_item that's
been embedded but not yet classified. This is the same "find pending work,
process it, flag it done" pattern as normaliser.py and the embedding
script — nothing new conceptually, just a third stage in the same chain.

Requires content_item_topics table and content_items.topic_classified
column to exist first (see the SQL above).
"""

import os
import json
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
import joblib

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

BATCH_SIZE = 500

# Load the model ONCE at startup — not per item. Training is expensive,
# but loading a saved model and calling .predict() on it is cheap and fast.
model = joblib.load("topic_classifier.joblib")


def parse_embedding(raw):
    """Same fix as train_classifier.py — pgvector comes back as a string, not a real list."""
    if isinstance(raw, str):
        return np.array(json.loads(raw), dtype=float)
    return np.array(raw, dtype=float)


def fetch_mean_pooled_embedding(content_item_id):
    """Identical logic to training — the model only makes sense if predictions
    use the exact same kind of input it was trained on."""
    result = (
        supabase.table("embeddings")
        .select("embedding")
        .eq("content_item_id", content_item_id)
        .execute()
    )
    if not result.data:
        return None
    vectors = np.array([parse_embedding(row["embedding"]) for row in result.data])
    return vectors.mean(axis=0)


def classify_pending():
    total_classified = 0

    while True:
        # Only items that are embedded (we need their vector) and not yet classified.
        result = (
            supabase.table("content_items")
            .select("id")
            .eq("embedded", True)
            .eq("topic_classified", False)
            .limit(BATCH_SIZE)
            .execute()
        )
        items = result.data
        if not items:
            break

        for item in items:
            content_item_id = item["id"]
            vector = fetch_mean_pooled_embedding(content_item_id)
            if vector is None:
                continue  # shouldn't happen if embedded=true, but don't crash the batch

            # model.predict() expects a 2D array (a batch of inputs), even for one item —
            # that's why vector goes in wrapped as [vector], and why we take [0] back out.
            predicted_topic = model.predict([vector])[0]

            try:
                supabase.table("content_item_topics").upsert({
                    "content_item_id": content_item_id,
                    "topic": predicted_topic,
                }).execute()
            except Exception as e:
                print(f"  ERROR inserting topic for item {content_item_id}: {e}")
                continue  # don't mark it classified if the insert failed — retry next run

            supabase.table("content_items").update(
                {"topic_classified": True}
            ).eq("id", content_item_id).execute()

            total_classified += 1

        print(f"  Classified {len(items)} items this batch (running total: {total_classified})")

    if total_classified == 0:
        print("Nothing pending — all embedded items already classified.")
    else:
        print(f"\nDone. {total_classified} items classified.")


if __name__ == "__main__":
    classify_pending()