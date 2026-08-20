import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_article(articles):

            response = (supabase.table("news_db")
                                .upsert(articles, on_conflict="url")
                                .execute())


def get_articles():

    response = (
            supabase
            .table("news_db")
            .select("url")
            .eq("is_scraped", False)
            .execute()
        )
    
    return response.data

def upsert_article(scraped_bodies):

    response = (supabase.table("news_db")
                        .upsert(scraped_bodies, on_conflict="url")
                        .execute())
    return response.data



def insert_mdpi_papers(articles):

            response = (supabase.table("mdpi_papers")
                                .upsert(articles, on_conflict="url")
                                .execute())

def get_articles_mdpi():

    response = (
            supabase
            .table("mdpi_papers")
            .select("url")
            .eq("is_scraped", False)
            .execute()
        )
    return response.data

def upsert_mdpi_papers(scraped_bodies):

    response = (supabase.table("mdpi_papers")
                        .upsert(scraped_bodies, on_conflict="url")
                        .execute())


def upsert_energy_articles(energy_device_articles):

    if energy_device_articles:

        response= (supabase.table("energybased_devices")
                            .upsert(energy_device_articles, on_conflict= "id")
                            .execute())
    else: 
          print("no energy based news today!")

    return response.data