from playwright.sync_api import sync_playwright


playwright = sync_playwright().start()

browser = playwright.chromium.launch(
    headless=False
)

page = browser.new_page()


def fetch_page(url):

    page.goto(url, timeout=60000)

    page.wait_for_selector("div.post")

    html = page.content()

    return html


def close_browser():

    browser.close()

    playwright.stop()