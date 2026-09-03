import time
from datetime import datetime, timedelta, UTC
from database import upsert_posts
from search import fetch_page
from parser import parse_page

keywords = ["medspa", "botox", "dermal filler", "kybella", "aesthetician", "injectables", "cool sculpting"]

REQUEST_DELAY_SECONDS = 5  # be polite — 7 keywords means 7x the requests of before
CUTOFF_DAYS = 5


def build_url(keyword, after=None):
    url = f"https://safereddit.com/r/popular/search?q={keyword}&sort=new"
    if after:
        url += f"&after=t3_{after}"
    return url


def parse_post_time(post):
    """Isolated so a single malformed date doesn't take down the whole crawl —
    returns None on failure instead of raising, and the caller decides what to do."""
    try:
        return datetime.strptime(post["created_at"], "%b %d %Y, %H:%M:%S UTC").replace(tzinfo=UTC)
    except (ValueError, KeyError) as e:
        print(f"  WARNING: couldn't parse date for post {post.get('post_id', '?')}: {e}")
        return None


def crawl_keyword(keyword, cutoff_time):
    """One keyword's full paginated crawl. Wrapped in try/except by the caller
    so a failure here doesn't stop the remaining keywords from running."""
    url = build_url(keyword)

    while True:
        html = fetch_page(url)
        posts = parse_page(html)
        if not posts:
            break

        print(f"[{keyword}] fetched {len(posts)} posts")

        valid_posts = []
        stop_crawling = False

        for post in posts:
            post_time = parse_post_time(post)
            if post_time is None:
                continue  # skip this one post, don't abandon the whole page over it

            if post_time < cutoff_time:
                stop_crawling = True
                break
            valid_posts.append(post)

        if valid_posts:
            upsert_posts(valid_posts)
            print(f"[{keyword}] inserted/updated {len(valid_posts)} posts")

        if stop_crawling:
            print(f"[{keyword}] reached posts older than {CUTOFF_DAYS} days.")
            break

        last_post_id = posts[-1]["post_id"]
        url = build_url(keyword, last_post_id)
        time.sleep(REQUEST_DELAY_SECONDS)


def crawl_posts():
    cutoff_time = datetime.now(UTC) - timedelta(days=CUTOFF_DAYS)

    for keyword in keywords:
        print(f"\n=== Starting keyword: {keyword} ===")
        try:
            crawl_keyword(keyword, cutoff_time)
        except Exception as e:
            # one keyword's failure shouldn't sink the other six
            print(f"ERROR crawling '{keyword}': {e} — moving to next keyword")
            continue
        time.sleep(REQUEST_DELAY_SECONDS)  # pause between keywords too, not just between pages