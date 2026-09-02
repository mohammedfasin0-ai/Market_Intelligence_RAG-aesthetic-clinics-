"""
Med Spa Industry Radar — dashboard v1

Run with: streamlit run app.py

Reads from topic_rollups (fast, pre-aggregated counts) for the charts,
and from content_items / content_item_topics (a real, un-aggregated
query) for the drill-down examples underneath.
"""

import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(page_title="Med Spa Industry Radar", layout="wide")


@st.cache_resource
def get_supabase_client():
    # cache_resource, not cache_data: this is a connection object, not query
    # results — we want exactly ONE client shared across reruns, not a fresh
    # connection every time the user clicks something.
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


supabase = get_supabase_client()


@st.cache_data(ttl=300)  # 5 minutes — rollups only update once a day anyway,
def fetch_rollups(start_date: str, end_date: str) -> pd.DataFrame:
    """cache_data (not cache_resource) because this returns plain data —
    Streamlit hashes the arguments (start_date, end_date) and reuses the
    result if you ask for the same range again within the TTL window."""
    result = (
        supabase.table("topic_rollups")
        .select("*")
        .gte("bucket_date", start_date)
        .lte("bucket_date", end_date)
        .execute()
    )
    return pd.DataFrame(result.data)


@st.cache_data(ttl=300)
def fetch_examples_for_topic(topic: str, start_date: str, limit: int = 8) -> pd.DataFrame:
    """The drill-down query — real items, not aggregated counts.
    Two calls because the Supabase REST client can't do a SQL JOIN directly:
    first find which content_item_ids have this topic, then fetch those items."""
    topic_links = (
        supabase.table("content_item_topics")
        .select("content_item_id")
        .eq("topic", topic)
        .execute()
    )
    item_ids = [row["content_item_id"] for row in topic_links.data]
    if not item_ids:
        return pd.DataFrame()

    items = (
        supabase.table("content_items")
        .select("title,url,source_type,posted_at,text_for_embedding")
        .in_("id", item_ids)
        .gte("posted_at", start_date)
        .order("posted_at", desc=True)
        .limit(limit)
        .execute()
    )
    df = pd.DataFrame(items.data)
    if not df.empty:
        df["preview"] = df["text_for_embedding"].str[:180]
    return df


@st.cache_data(ttl=300)
def fetch_recent_activity(limit: int = 15) -> pd.DataFrame:
    result = (
        supabase.table("content_items")
        .select("title,url,source_type,posted_at")
        .order("posted_at", desc=True)
        .limit(limit)
        .execute()
    )
    return pd.DataFrame(result.data)


# ---- Sidebar: date range control ----
st.sidebar.header("Time window")
days_back = st.sidebar.radio("Show data from the last:", [1, 3, 7, 14], index=2, format_func=lambda d: f"{d} day(s)")
start_date = (date.today() - timedelta(days=days_back)).isoformat()
end_date = date.today().isoformat()

st.title("Med Spa Industry Radar")
st.caption(f"Showing activity from {start_date} to {end_date}")

rollups_df = fetch_rollups(start_date, end_date)

if rollups_df.empty:
    st.warning("No rollup data for this window yet.")
else:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("What's trending")
        topic_totals = rollups_df.groupby("topic")["item_count"].sum().sort_values(ascending=False)
        st.bar_chart(topic_totals)

    with col2:
        st.subheader("Volume over time")
        daily_totals = rollups_df.groupby("bucket_date")["item_count"].sum().sort_index()
        st.line_chart(daily_totals)

    st.divider()

    # ---- Drill-down ----
    st.subheader("See what's actually being discussed")
    selected_topic = st.selectbox("Pick a topic:", topic_totals.index.tolist())

    examples_df = fetch_examples_for_topic(selected_topic, start_date)
    if examples_df.empty:
        st.info("No examples found for this topic in the selected window.")
    else:
        for _, row in examples_df.iterrows():
            title = row["title"] or "(no title — likely a comment)"
            if row["url"]:
                st.markdown(f"**[{title}]({row['url']})** — {row['source_type']}, {row['posted_at'][:10]}")
            else:
                st.markdown(f"**{title}** — {row['source_type']}, {row['posted_at'][:10]}")
            st.caption(row["preview"])
            st.markdown("---")

st.divider()

# ---- Recent activity feed (always shown, not filtered by topic) ----
st.subheader("Recent activity across all sources")
activity_df = fetch_recent_activity()
if not activity_df.empty:
    display_df = activity_df.copy()
    display_df["posted_at"] = display_df["posted_at"].str[:10]
    st.dataframe(display_df, width=True, hide_index=True)