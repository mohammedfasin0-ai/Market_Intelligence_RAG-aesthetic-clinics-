import html
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta

url = "https://modernaesthetics.com/medical-news/energy-based-devices/"
BASE_URL = "https://www.modernaesthetics.com"

DATE_FORMAT = "%m/%d/%Y"
CUTOFF_DAYS = 3


def get_energydevice_news():

    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select(".news-list-item")

    if not items:
        print("no items found")
        return None

    results = []

    today = datetime.now()
    cutoff_date = today - timedelta(days=CUTOFF_DAYS)

    for item in items:

        news_id = item.get("data-id")
        title = item.get("data-title")
        publication_date = item.get("data-date-of-publication")

        # -----------------------------
        # Date filtering
        # -----------------------------
        parsed_date = None
        if publication_date:
            try:
                parsed_date = datetime.strptime(publication_date, DATE_FORMAT)
            except ValueError:
                # unexpected date format — skip filtering for this item, or
                # treat it as invalid and skip the item entirely, your call
                parsed_date = None

        if parsed_date and parsed_date < cutoff_date:
            # older than 30 days — skip this one
            continue

        relative_url = item.get("data-url")
        article_url = urljoin(BASE_URL, relative_url) if relative_url else None

        category_element = item.select_one(".block-description__tag")
        category = (
            category_element.get_text(" ", strip=True)
            if category_element
            else None
        )

        raw_description = item.get("data-description")
        description_text = None
        if raw_description:
            unescaped = html.unescape(raw_description)
            desc_soup = BeautifulSoup(unescaped, "html.parser")
            description_text = desc_soup.get_text(" ", strip=True)

        raw_subtitle = item.get("data-subtitle")
        key_takeaways = []
        if raw_subtitle:
            unescaped_sub = html.unescape(raw_subtitle)
            sub_soup = BeautifulSoup(unescaped_sub, "html.parser")
            key_takeaways = [
                li.get_text(" ", strip=True)
                for li in sub_soup.find_all("li")
            ]

        results.append({
            "id": news_id,
            "title": title,
            "published_at": publication_date,
            "url": article_url,
            "category": category,
            "body": description_text,
            "key_takeaways": key_takeaways,
        })

    return results