from datetime import datetime, timedelta, UTC
from database import upsert_posts
from search import fetch_page
from parser import parse_page

keyword = "medspa"


def build_url(keyword, after=None):

    url = f"https://safereddit.com/r/popular/search?q={keyword}&sort=new"

    if after:
        url += f"&after=t3_{after}"

    return url


# -------- FIRST PAGE --------
def crawl_posts():

    url = build_url(keyword)

    cutoff_time = datetime.now(UTC) - timedelta(days=1)

    while True:

        html = fetch_page(url)

        posts = parse_page(html)
        if not posts:
            break

        print(f"fetched {len(posts)} posts")

        valid_posts = []
        stop_crawling = False

        for post in posts:

            post_time = datetime.strptime(post["created_at"], "%b %d %Y, %H:%M:%S UTC").replace(tzinfo=UTC)

            if post_time < cutoff_time:
                stop_crawling = True
                break
            valid_posts.append(post)

        if valid_posts:
            upsert_posts(valid_posts)
            print(f"Inserted/updated {len(valid_posts)} posts")

        last_post_id = posts[-1]["post_id"]

        if stop_crawling:
            print("Reached posts older than 30 days.")
            break

        url = build_url(keyword, last_post_id)