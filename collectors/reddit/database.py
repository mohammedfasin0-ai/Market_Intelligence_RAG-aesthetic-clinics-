from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upsert_posts(posts):

    response = (supabase.table("reddit_posts")
                        .upsert(posts, on_conflict="post_id")
                        .execute())
    return response