import os, requests
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("YT_TRANSCRIPT_API")

url = 'https://transcriptapi.com/api/v2/youtube/transcript'
params = {'video_url': 'https://www.youtube.com/watch?v=lHuBotAyAKc', 'format': 'json'}
r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + API_KEY}, timeout=30)
r.raise_for_status()
print(r.json()['transcript'])
