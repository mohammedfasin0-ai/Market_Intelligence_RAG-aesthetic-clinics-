from comment_database import get_posts, upsert_comments, mark_comments_scraped
from comment_search import fetch_comment_page
from comment_parser import parse_comments
import time

def crawl_comments():

    posts = get_posts()

    print(f"Found {len(posts)} posts\n")

    for post in posts:

        print ("=" * 60)
        print(f"procesing post: {post["post_id"]}")
        print(post["url"])

        try: 
            html = fetch_comment_page(post["url"])

            comments = parse_comments(html, post["post_id"])

            print(f"Found {len(comments)} comment\n")

            if comments:

                upsert_comments(comments)

                print (f"upserted {len(comments)} into database")

            mark_comments_scraped(post["post_id"])

            print(f"Marked {post['post_id']}) as comments scraped!")

            time.sleep(7)

        except Exception as e:
            print(f"Failed to process post {post['post_id']}")
            print(e)
            print()


            

        