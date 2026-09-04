import time
from datetime import datetime, timedelta, UTC
from database import upsert_posts
from search import fetch_page
from parser import parse_page

# Subreddits identified as genuinely relevant to the industry — found organically
# in samples pulled during the earlier sitewide keyword-search crawler. Replaces
# keyword matching entirely: no search query, no risk of an unrelated subreddit's
# post sneaking in just because it happened to mention "medspa" once.
subreddits = [
    "MedSpa",
    "Estheticians",
    "DermatologyQuestions",
    "DermatologyPA",
    "cosmeticsurgery",
    "PeptideTides",
    "TirzepatideRX",
    "compoundedtirzepatide",
    "AcneTreatments",
    "Microneedling",
    "45PlusSkincare",
    "MedspaUSA",
    "DIYaesthetics",
    "BotoxSupportCommunity",
    "aestheticnursing",
    "Esthetics",
    "PlasticSurgery",
    "30PlusSkinCare",
    "KoreaSeoulBeauty",
    "Zepbound",
]

REQUEST_DELAY_SECONDS = 5
CUTOFF_DAYS = 5  # change this single number whenever you want a different window — nothing else needs editing


def build_url(subreddit, after=None):
    # First page: bare /new listing, no query params at all.
    # Subsequent pages: add the pagination cursor exactly as Reddit's own "next" link does.
    url = f"https://safereddit.com/r/{subreddit}/new"
    if after:
        url += f"?sort=new&t=&after=t3_{after}"
    return url


def parse_post_time(post):
    """Isolated so a single malformed date doesn't take down the whole crawl —
    returns None on failure instead of raising, and the caller decides what to do."""
    try:
        return datetime.strptime(post["created_at"], "%b %d %Y, %H:%M:%S UTC").replace(tzinfo=UTC)
    except (ValueError, KeyError) as e:
        print(f"  WARNING: couldn't parse date for post {post.get('post_id', '?')}: {e}")
        return None


def crawl_subreddit(subreddit, cutoff_time):
    """One subreddit's full paginated crawl through /new. Wrapped in try/except
    by the caller so a failure here doesn't stop the remaining subreddits from running."""
    url = build_url(subreddit)

    while True:
        html = fetch_page(url)
        posts = parse_page(html)
        if not posts:
            break

        print(f"[r/{subreddit}] fetched {len(posts)} posts")

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
            print(f"[r/{subreddit}] inserted/updated {len(valid_posts)} posts")

        if stop_crawling:
            print(f"[r/{subreddit}] reached posts older than {CUTOFF_DAYS} days.")
            break

        last_post_id = posts[-1]["post_id"]
        url = build_url(subreddit, last_post_id)
        time.sleep(REQUEST_DELAY_SECONDS)


def crawl_posts():
    cutoff_time = datetime.now(UTC) - timedelta(days=CUTOFF_DAYS)

    for subreddit in subreddits:
        print(f"\n=== Starting r/{subreddit} ===")
        try:
            crawl_subreddit(subreddit, cutoff_time)
        except Exception as e:
            # one subreddit's failure shouldn't sink the rest
            print(f"ERROR crawling r/{subreddit}: {e} — moving to next subreddit")
            continue
        time.sleep(REQUEST_DELAY_SECONDS)  # pause between subreddits too, not just between pages