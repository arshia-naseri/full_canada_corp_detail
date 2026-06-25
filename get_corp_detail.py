import os
import time
import json
import requests

API_KEY = 'fdce5d047c47ae3918f01619d87e423f'

HEADERS = {
    "user-key": API_KEY,
    "Accept-Language": "en",
}

BASE_URL = "https://apigateway-passerelledapi.ised-isde.canada.ca/corporations/api"

corporation_ids = [
    "4014",
    # add more corporation numbers here
]

def get_with_retry(url, headers, timeout=60, max_retries=5):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 2 ** attempt))
            print(f"Rate limited. Waiting {wait}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response
    raise Exception(f"Failed after {max_retries} retries: {url}")

def clean_v1(data):
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return item
    return data

with open("ised_full_corporation_details.jsonl", "w", encoding="utf-8") as f:
    for corp_id in corporation_ids:
        corp_url = f"{BASE_URL}/v1/corporations/{corp_id}.json?lang=eng"
        directors_url = f"{BASE_URL}/v2/corporations/{corp_id}/directors"

        corp_response = get_with_retry(corp_url, HEADERS)
        directors_response = get_with_retry(directors_url, HEADERS)

        record = {
            "corporation_id": corp_id,
            "corporation": clean_v1(corp_response.json()),
            "directors": directors_response.json(),
        }

        f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(f"Saved {corp_id}")

        # 60/minute max, 2 calls/corp → need ≥2s between corps
        time.sleep(2.0)