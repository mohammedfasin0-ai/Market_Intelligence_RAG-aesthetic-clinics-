from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_posts():

    response = (
        supabase
        .table("reddit_posts")
        .select("post_id, url")
        .eq("comments_scraped", False)
        .execute()
    )

    return response.data

def upsert_comments(comments):
    response = (supabase.table("reddit_post_comments")
                        .upsert(comments, on_conflict= "comment_id" )
                        .execute())
    return response

def mark_comments_scraped(post_id):
    response = (supabase.table("reddit_posts").update({"comments_scraped": True}).eq("post_id", post_id).execute())
    return response

