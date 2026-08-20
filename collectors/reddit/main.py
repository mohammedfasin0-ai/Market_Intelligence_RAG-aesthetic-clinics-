from crawler import crawl_posts
from comment_crawler import crawl_comments
from search import close_browser


def main():

    try:

        print("=" * 60)
        print("STARTING POST CRAWLER")
        print("=" * 60)

        crawl_posts()


        print("\n")
        print("=" * 60)
        print("STARTING COMMENT CRAWLER")
        print("=" * 60)

        crawl_comments()


    finally:

        print("\n")
        print("=" * 60)
        print("CLOSING BROWSER")
        print("=" * 60)

        close_browser()


if __name__ == "__main__":
    main()