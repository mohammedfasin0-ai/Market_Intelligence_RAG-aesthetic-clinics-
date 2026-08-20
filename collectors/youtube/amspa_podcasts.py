import os 
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client
import time


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YT_TRANSCRIPT_API = os.getenv("YT_TRANSCRIPT_API")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
channel_id = "UC67oWsoscR1MDgFozbYEYHg"

url = "https://www.googleapis.com/youtube/v3/playlistItems"

params = {
    "part": "snippet,contentDetails",
    "playlistId": "UU67oWsoscR1MDgFozbYEYHg",
    "maxResults": 50,
    "key": YOUTUBE_API_KEY
}

response = requests.get(url, params=params)

datas = response.json()

cutoff = datetime.now(timezone.utc) - timedelta(days=30)

print(type(datas))

all_list = []

def get_yt_metadata():

    for data in datas['items']:

        published_date = datetime.fromisoformat(
            data["contentDetails"]["videoPublishedAt"].replace("Z", "+00:00")
        )

        if published_date >= cutoff:
            title = data['snippet']['title']
            video_id = data['snippet']['resourceId']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            posted_at = published_date.isoformat().replace("Z", "+00:00")

            item_dict = {
                "title": title,
                "video_id": video_id,
                "video_url": video_url,
                "published_date": posted_at
            }

            all_list.append(item_dict)

    print (all_list)
    return all_list

all_list = get_yt_metadata()

def get_transcript(all_list):

    for list in all_list:

        video_url= list['video_url']

        url = 'https://transcriptapi.com/api/v2/youtube/transcript'
        params = {'video_url': video_url, 'format': 'json'}
        r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + YT_TRANSCRIPT_API}, timeout=30)
        r.raise_for_status()
        transcript_data= r.json()['transcript']
        clean_text = " ".join([item['text'] for item in transcript_data])

        list['transcript'] = clean_text

        

        time.sleep(5)

    return all_list

transcripts = get_transcript(all_list)


def upsert_YT_elements (transcripts):
    supabase.table("Amspa_podcasts")\
            .upsert(transcripts, on_conflict= "video_id")\
            .execute()

upsert_YT_elements(transcripts)