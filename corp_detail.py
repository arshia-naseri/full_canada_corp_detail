import json
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


class RateLimiter:
    """Token bucket: max `rate` calls per minute across all threads."""
    def __init__(self, calls_per_minute):
        self.interval = 60.0 / calls_per_minute
        self.lock = threading.Lock()
        self.last = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            gap = self.interval - (now - self.last)
            if gap > 0:
                time.sleep(gap)
            self.last = time.monotonic()


class CorpDetailFetcher:
    API_KEY = "fdce5d047c47ae3918f01619d87e423f"
    BASE_URL = "https://apigateway-passerelledapi.ised-isde.canada.ca/corporations/api"
    DEFAULT_OUTPUT_FILE = "ised_full_corporation_details.jsonl"

    def __init__(self, corporation_ids: list[str], output_file: str = DEFAULT_OUTPUT_FILE):
        self.corporation_ids = corporation_ids
        self.output_file = output_file
        self.headers = {
            "user-key": self.API_KEY,
            "Accept-Language": "en",
        }
        self.rate_limiter = RateLimiter(calls_per_minute=55)
        self.write_lock = threading.Lock()

    def _get_with_retry(self, url, timeout=60, max_retries=5):
        for attempt in range(max_retries):
            self.rate_limiter.wait()
            response = requests.get(url, headers=self.headers, timeout=timeout)
            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", 2 ** attempt))
                print(f"Rate limited. Waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response
        raise Exception(f"Failed after {max_retries} retries: {url}")

    @staticmethod
    def _clean_v1(data):
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    return item
        return data

    def _fetch_corp(self, corp_id: str) -> dict:
        corp_url = f"{self.BASE_URL}/v1/corporations/{corp_id}.json?lang=eng"
        directors_url = f"{self.BASE_URL}/v2/corporations/{corp_id}/directors"

        corp_response = self._get_with_retry(corp_url)
        directors_response = self._get_with_retry(directors_url)

        return {
            "corporation_id": corp_id,
            "corporation": self._clean_v1(corp_response.json()),
            "directors": directors_response.json(),
        }

    def _write(self, mode: str):
        """Fetch self.corporation_ids and write/append to output_file."""
        with open(self.output_file, mode, encoding="utf-8") as f:
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(self._fetch_corp, corp_id): corp_id for corp_id in self.corporation_ids}
                for future in as_completed(futures):
                    corp_id = futures[future]
                    try:
                        record = future.result()
                        with self.write_lock:
                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        print(f"Saved {corp_id}")
                    except Exception as e:
                        print(f"Failed {corp_id}: {e}")

    def run(self):
        """Full overwrite: fetch all corporation_ids and write fresh JSONL."""
        self._write("w")

    def append(self):
        """Append-only: fetch corporation_ids and append to existing JSONL."""
        self._write("a")

    def remove(self, removed_ids: list[str]):
        """Remove records whose corporation_id is in removed_ids from the JSONL file."""
        removed_set = set(removed_ids)
        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return

        kept = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("corporation_id") not in removed_set:
                    kept.append(line)
            except json.JSONDecodeError:
                kept.append(line)

        with open(self.output_file, "w", encoding="utf-8") as f:
            for line in kept:
                f.write(line + "\n")

        print(f"Removed {len(lines) - len(kept)} records from {self.output_file}")


if __name__ == "__main__":
    fetcher = CorpDetailFetcher(corporation_ids=["4014"])
    fetcher.run()
