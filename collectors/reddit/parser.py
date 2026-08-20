from bs4 import BeautifulSoup

BASE_URL = "https://safereddit.com"

def parse_page(html):

    soup = BeautifulSoup(html, "html.parser")

    posts = soup.find_all("div", class_="post")

    all_posts= []

    for post in posts:

        post_data= {}

        post_data["post_id"]= post["id"]

        title= post.find("h2", class_="post_title")

        post_data["title"] = title.get_text(strip= True)

        post_link = title.find("a", href = lambda href: href and "/comments/" in href)

        post_data["url"] = BASE_URL + post_link["href"]

        header = post.find("p", class_="post_header")

        post_data["subreddit"] = header.find("a", class_="post_subreddit").get_text(strip=True)

        header= post.find("p", class_="post_header")
        post_data["author"]= header.find("a", class_="post_author").get_text(strip=True)

        created= header.find("span", class_="created")
        post_data["created_at"] = created["title"]

        score= post.find("div", class_="post_score")
        score_text = score["title"]

        if score_text.isdigit():
            post_data["score"]= int(score_text)
        else:
            post_data["score"] = None

        comments= post.find("a", class_= "post_comments")
        comment_text= comments["title"]
        post_data["comment_count"] = int(comment_text.split()[0])

        body = post.find("div", class_="md")

        if body:
            post_data["body"] = body.get_text("", strip= True)
        else:
            post_data["body"] = ""    

        all_posts.append(post_data)

    return all_posts
