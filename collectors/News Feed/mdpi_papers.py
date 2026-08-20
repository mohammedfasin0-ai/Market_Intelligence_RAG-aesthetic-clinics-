from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime

def get_recent_articles(search_query: str, max_days: int = 5) -> list:
    """
    Scrapes MDPI search results for a query and returns articles published 
    within the specified maximum number of days.
    """
    # Replace any plus signs with standard spaces for MDPI's search engine
    clean_query = search_query.replace('+', ' ')
    url = f"https://mdpi.com/search?q={clean_query}"
    base_url = "https://mdpi.com"
    all_news = []
    today = datetime.now()

    print(f"Navigating to MDPI search URL: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()
        page.goto(url, timeout=60000)

        # Handle infinite scroll loading
        last_height = page.evaluate("document.body.scrollHeight")
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            page.wait_for_timeout(2000)  # Give JS time to load more cards
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("div", class_="article-content")
    
    print(f"Found {len(articles)} raw HTML article elements on the page.")

    for article in articles:
        target_div = article.find("div", class_="color-grey-dark")
        if not target_div:
            continue
            
        full_text = target_div.get_text()
        date_alone = full_text.split('-')[-1].strip()
        
        try:
            date_obj = datetime.strptime(date_alone, "%d %b %Y")
        except ValueError:
            continue # Skip if date format doesn't match layout expectations
        
        # Calculate article age
        age_in_days = (today - date_obj).days
        
        # CHANGED: Use 'continue' instead of 'break' because MDPI results are not sorted by date!
        if age_in_days > max_days:
            continue

        # Format date consistently as YYYY-MM-DD
        formatted_date = date_obj.strftime("%Y-%m-%d")

        title_nest = article.find("a", class_="UD_Listings_ArticlePDF")
        title = title_nest['data-name'] if title_nest else "No Title"

        link_nest = article.find("a", class_="title-link")
        link = f"{base_url}{link_nest['href']}" if link_nest else "No Link"

        author_nest = article.find_all('strong')
        author_list = [tag.get_text(strip=True) for tag in author_nest if tag.get_text(strip=True) != "Abstract"]
        author = ", ".join(author_list)

        category_nest = article.select_one("div.belongsTo a")
        category = category_nest.get_text(strip=True) if category_nest else "Not Found"

        upsert_dict = {
            'url': link,
            'title': title,
            'category': category,
            'authors': author,
            'published_at': formatted_date,
            'is_scraped': False
        }

        all_news.append(upsert_dict)

    print(f"Successfully collected {len(all_news)} articles within the {max_days}-day limit.")
    return all_news


def scrape_mdpi_urls(mdpi_urls):

    body_list= []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for url_ in mdpi_urls:

            url = url_['url']


            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_selector(".html-p", timeout=30000)

            html = page.content()

            soup = BeautifulSoup(html, "html.parser")

            paragraphs = soup.select(".html-p")

            body = "\n\n".join(
            p.get_text(" ", strip=True)
            for p in paragraphs
            if p.get_text(strip=True)
    )
            url_body = {
                'url': url,
                'body': body,
                'is_scraped': 'TRUE'
            }

            body_list.append(url_body)

        browser.close()

    return body_list







