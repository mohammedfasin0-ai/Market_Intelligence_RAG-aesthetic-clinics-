from search import fetch_page

def fetch_comment_page(post_url):
    html = fetch_page(post_url)

    return html 