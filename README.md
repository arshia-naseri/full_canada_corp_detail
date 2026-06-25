# 🍁 Canada Gov Corporation Scraper

Fetches active business corporation data from Canadian government APIs and stores it locally.

## What It Does

1. **Corp List** — pulls all active business corporations from the CKAN datastore (Corporations Canada open data), saves to CSV, computes delta vs previous run
2. **Corp Detail** — fetches full corporation info + directors from ISED API for each corp ID, writes to JSONL
3. **Main** — orchestrates both: on first run writes everything; on subsequent runs only fetches added/removed corps (delta mode)

## 📂 Output Files

| File | Description |
|------|-------------|
| `active_business_corps.csv` | Full corp list (current run) |
| `old_active_business_corps.csv` | Previous run backup |
| `delta_active_business_corps.csv` | Added/removed corps since last run |
| `ised_full_corporation_details.jsonl` | Full details + directors per corp (one JSON per line) |

## ⚙️ Setup

```bash
pip install -r requirements.txt
```

## 🚀 Usage

```bash
python main.py
```

**First run:** fetches full list → fetches all corp details → writes JSONL from scratch.

**Subsequent runs:** fetches new list → diffs vs backup → fetches details only for added corps → removes deleted corps from JSONL.

## 🚦 Rate Limiting

ISED API capped at 55 calls/min. `RateLimiter` token bucket enforces this across 8 concurrent threads. 429 responses trigger exponential backoff (up to 5 retries).

## 🌐 Data Sources

| Source | API |
|--------|-----|
| Corp list | `demo.datashades.com` — CKAN datastore, resource `7b6dd154-aa04-46ce-8880-ce4a5fa0a680` |
| Corp details + directors | `apigateway-passerelledapi.ised-isde.canada.ca/corporations/api` |

## 🗂️ Project Structure

```
main.py          # Entry point
corp_list.py     # CorpListFetcher — downloads + diffs corp list
corp_detail.py   # CorpDetailFetcher — fetches detail + directors per corp
requirements.txt
```
