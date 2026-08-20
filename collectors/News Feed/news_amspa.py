import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


URL = "https://www.americanmedspa.org/articles-and-news/"
AJAX_URL = "https://www.americanmedspa.org/wp-admin/admin-ajax.php"

cutoff_date = datetime.now() - timedelta(days=3)

def parse_articles(html):

    soup = BeautifulSoup(html, "html.parser")

    articles = soup.find_all(
        "article",
        class_="abh-card"
    )

    article_batch = []

    for article in articles:

        title_element = article.find(
            "h3",
            class_="abh-card__title"
        )

        link_element = title_element.find("a")

        date_element = article.find(
            "span",
            class_="abh-card__date"
        )

        author = article.find("span", class_ = "abh-card__author")

        category = article.find("span", class_= "abh-card__category")

        article_data = {
            "title": title_element.get_text(strip=True),
            "url": link_element["href"],
            "created_at": date_element.get_text(strip=True),
            "author": author.get_text(strip= True),
            "category": category.get_text(strip=True), 
            "is_scraped": False
         }

        article_batch.append(article_data)

    return article_batch


def initial_batch():

    response = requests.get(URL)

    response.raise_for_status()

    return parse_articles(response.text)


def get_next_page(page):

    payload = {
        "action": "amspa_blog_load",
        "page": page,
        "per_page": 11,
        "category": "all",
        "search": "",
        "exclude": 19834
    }

    response = requests.post(
        AJAX_URL,
        data=payload
    )

    response.raise_for_status()

    data = response.json()

    html = data["data"]["html"]

    return parse_articles(html)


def collect_articles():

    all_articles = []

    page = 1

    current_batch = initial_batch()

    while True:

        for article in current_batch:

            post_date = datetime.strptime(
                article["created_at"],
                "%b %d, %Y"
            )

            if post_date < cutoff_date:

                print(
                    f"Reached cutoff: {article['title']}"
                )

                return all_articles

            all_articles.append(article)

        page += 1

        print(f"Fetching page {page}...")

        current_batch = get_next_page(page)

scraped_bodies= []

def scrape_urls(urls):

    i= 0

    for url in urls:

        url_ = url['url']
    
        response = requests.get(url_)

        soup = BeautifulSoup(response.text, "html.parser")

        content = soup.find("main", class_ = "clearfix width-100")

        body = content.get_text(strip= True)

        second_upsert= {
            "url": url_,
            "body": body,
            "is_scraped": True
        }

        scraped_bodies.append(second_upsert)

        i= i+1

        print(f"got the {i} url content")

    return scraped_bodies
