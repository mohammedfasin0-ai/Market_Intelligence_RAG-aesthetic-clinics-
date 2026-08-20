import requests
import time
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def supabase_retrieval():
    response = supabase.table("Amspa_podcasts")\
                       .select("video_url", "video_id")\
                       .is_( "transcript", "null")\
                       .execute()
    print(response)
    return response

url= supabase_retrieval()

def do_the_api (url_db):

    url_ = url_db.data

    url = url_[0]['video_url']

    all_list = []

    url_api = "https://api-v1.saveto.ai/api/v2/app/tr/platform"

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,ml;q=0.8',
        'content-type': 'application/json',
        'fp': '17faa4c12afca83dfff7ba2eb474c65f',
        'fp1': 'AhjucIFXW30jS14Z6DJ0rtFtyzo7E8A7/D5iEgmCD3u5SV4uUPqWOkdvNk0ywQBP',
        'origin': 'https://saveto.ai',
        'priority': 'u=1, i',
        'referer': 'https://saveto.ai/',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'theme-version': '83EmcUoQTUv50LhNx0VrdcK8rcGexcP35FcZDcpgWsAXEyO4xqL5shCY6sFIWB2Q',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'x-code': '1786891043167',
        'x-guide': 'G2Z+SbSzLTe95CszukBjgU/7v9CclFAQqM0shV+GWeXZ+saH2W7PuxPEiT1no7XS7SiVVLayS9936Ycfbp8/9kaphcrawVSKkr+IzqMZf8Whn0khyd/gmNsJ6nz0z+o268xoaZ+64b0XWk5IUaI7yKeYjUAPt8W6sfLqOhBdxoo=',
    }

    json_data = {
        'url': url,
        'platform': 1,
        'language': 'en',
        'request_from': 23,
        'origin_from': 'cd14b9bd8ecfac7d',
    }

    response = requests.post(url_api, headers=headers, json=json_data)

    response_data = response.json()

    if "data" in response_data:
        data = response_data['data']
        print(data)

        headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,ml;q=0.8',
        'fp': '17faa4c12afca83dfff7ba2eb474c65f',
        'fp1': 'HJy5/BicnagDaa6pFJ8fG1o3TONnxmNER50FAzI8BI4kq9gxKF+IfYulCOBw8n8S',
        'origin': 'https://saveto.ai',
        'priority': 'u=1, i',
        'referer': 'https://saveto.ai/',
        'sec-ch-ua': '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'theme-version': '83EmcUoQTUv50LhNx0VrdcK8rcGexcP35FcZDcpgWsAXEyO4xqL5shCY6sFIWB2Q',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'x-code': '1786891048566',
        'x-guide': 'CTP9LTZoYoaGnL805Oghb9dPDkTqvk7NC4p5xwrFP6N9Qk7V2z6JGxGpU/PRfmcOq62ZMVUYf8bxonzAt+7BPN0q12qCokM/v3vJlvWDmfpytNsMvwxKdNjqJog1SOg+NFfvLuqqN+0IBlO/tkBvM68cQAvMzoBaZBzSLQCbPv4=',
    }

        params = {
            'task_id': data,
            'request_from': '23',
            'origin_from': 'cd14b9bd8ecfac7d',
        }

        time.sleep(10)
        response_second = requests.get('https://api-v1.saveto.ai/api/app/task/check_status', params=params, headers=headers)

        response_data_second = response_second.json()

        print(response_data_second)

        pure_data = response_data_second['data']
        text = pure_data['data']

        for items in text:

            full_text = items.get('text')
            text_imp = full_text.replace("&gt;&gt;", "")
            print(text_imp)
        

do_the_api(url)

