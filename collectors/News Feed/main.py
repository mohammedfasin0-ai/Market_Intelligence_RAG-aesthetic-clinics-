from news_amspa import collect_articles, scrape_urls
from database_news import insert_article, get_articles, upsert_article, get_articles_mdpi, insert_mdpi_papers, upsert_mdpi_papers, upsert_energy_articles
from mdpi_papers import get_recent_articles, scrape_mdpi_urls
from energybased_devices import get_energydevice_news
def main():
    print("Starting news discovery...")
    articles = collect_articles()

    # Only run this block if articles were actually found
    if articles:
        print(f"Collected {len(articles)} articles.")

        print("Upserting articles into Supabase...")
        insert_article(articles)
        print("Done.")

        print("getting links from the database")
        urls = get_articles()
        print("links acquired")

        bodies = scrape_urls(urls)
        print("bodies acquired")

        upsert_article(bodies)
        print(f"upserted {len(bodies)} bodies into the database")
    else:
        print("No primary articles found today! Skipping to MDPI news...")

    # This section will now run regardless of whether primary articles were found
    print("now mdpi news articles")
    from_mdpi = get_recent_articles("aesthetic+medicine")

    if from_mdpi:
        insert_mdpi_papers(from_mdpi)
        print("inserted mdpi article into database")


        print("getting unscraped mdpi urls")
        mdpi_urls = get_articles_mdpi()

        print("scraping unscraped urls")
        scraped_mdpi_bodies = scrape_mdpi_urls(mdpi_urls)

        print("upserting scraped bodies into the database")
        upsert_mdpi_papers(scraped_mdpi_bodies)
        print("upsert done!")
    else:
        print("no mdpi papers today!")

    print("now energy based devices news")
    energy_device_articles = get_energydevice_news()
    result = upsert_energy_articles(energy_device_articles)
    if result:
        print("upserted energy devices news into db")
    else: 
        print("No items Found!")


if __name__ == "__main__":
    main()
