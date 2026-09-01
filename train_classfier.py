"""
Train the topic classifier.

Reads bootstrap_labels.csv (content_item_id + LLM-assigned primary_topic),
fetches the matching embedding(s) for each item, mean-pools multi-chunk
items into a single vector, then trains a logistic regression classifier
with class_weight='balanced' to account for the imbalance we found
(Business Operations: 167 examples vs. Product & Device Launches: 13).

This does NOT write anything to Supabase — it trains locally and saves
the model to a file for review before it's wired into anything live.
"""

import os
import csv
import json
import numpy as np
from dotenv import load_dotenv
from supabase import create_client
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def parse_embedding(raw):
    """
    Supabase's REST API doesn't know how to serialize Postgres's native
    `vector` type — it comes back as a STRING that looks like a list,
    e.g. "[0.0123, -0.045, ...]", not an actual Python list of floats.
    Feeding that straight into np.array() gives you an array of strings,
    which is why the earlier run crashed trying to average them.
    """
    if isinstance(raw, str):
        return np.array(json.loads(raw), dtype=float)
    return np.array(raw, dtype=float)


def load_bootstrap_labels(path="bootstrap_labels.csv"):
    """Read the CSV back into (content_item_id, primary_topic) pairs."""
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append((int(row["content_item_id"]), row["primary_topic"]))
    return rows


def fetch_mean_pooled_embedding(content_item_id):
    """
    A content_item can have multiple chunks in `embeddings` (long papers
    especially). We need exactly one vector per item, so we average
    every chunk's embedding together, dimension by dimension.
    """
    result = (
        supabase.table("embeddings")
        .select("embedding")
        .eq("content_item_id", content_item_id)
        .execute()
    )
    if not result.data:
        return None  # shouldn't happen if the pipeline is in sync, but don't crash if it does

    # Each row's "embedding" comes back as a STRING from Supabase's REST API
    # (see parse_embedding above) — parse each one into real floats first,
    # then stack them into a matrix (num_chunks x 384), then average down
    # the rows (axis=0) -> one (384,) vector representing the whole item,
    # regardless of chunk count.
    vectors = np.array([parse_embedding(row["embedding"]) for row in result.data])
    return vectors.mean(axis=0)


def build_dataset():
    labels = load_bootstrap_labels()
    print(f"Loaded {len(labels)} bootstrap labels. Fetching embeddings...")

    X, y = [], []
    skipped = 0
    for i, (content_item_id, topic) in enumerate(labels, 1):
        vector = fetch_mean_pooled_embedding(content_item_id)
        if vector is None:
            skipped += 1
            continue
        X.append(vector)
        y.append(topic)
        if i % 100 == 0:
            print(f"  fetched {i}/{len(labels)}")

    print(f"Built dataset: {len(X)} items ({skipped} skipped — no embedding found)")
    return np.array(X), np.array(y)


def main():
    X, y = build_dataset()

    # Split into train/test BEFORE touching class_weight — we need an honest,
    # never-seen-during-training set to check if the model actually generalizes.
    # stratify=y keeps the same class proportions in both splits — without this,
    # a random split could easily put zero "Product & Device Launches" (only 13
    # total) into the test set, making that class impossible to evaluate.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train)}  Test: {len(X_test)}")

    # class_weight='balanced' automatically penalizes mistakes on rare classes
    # more heavily during training, roughly in proportion to how rare they are —
    # this is the fix for the 167-vs-13 imbalance, with zero synthetic data.
    # max_iter raised from sklearn's default of 100, since 384 input dimensions
    # and 11 output classes need more optimization steps to converge cleanly.
    model = LogisticRegression(class_weight="balanced", max_iter=2000)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    # This is the real report — precision/recall PER CLASS, not just one
    # overall accuracy number. Overall accuracy can look fine while the
    # model is quietly terrible at the rare classes we actually care about
    # getting right (Safety Incidents, Product & Device Launches).
    print("\n=== Per-class performance on held-out test set ===")
    print(classification_report(y_test, predictions))

    joblib.dump(model, "topic_classifier.joblib")
    print("Model saved to topic_classifier.joblib")


if __name__ == "__main__":
    main()