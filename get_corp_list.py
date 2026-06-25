import csv
import os
import shutil
import requests

API_URL = "https://demo.datashades.com/api/3/action/datastore_search"

RESOURCE_ID = "7b6dd154-aa04-46ce-8880-ce4a5fa0a680"  # Active business corporations

''' "Corporation number", "Business number (BN)", "Corporate name - form 1", 
    "Corporate name - form 2", "Governing legislation", "Status", "Anniversary date", "Year of last annual filing", 
    "Date of last annual meeting", "Street", "Street 2", "City/town", "Province/territory", "Country", "Postal code", 
    "Minimum number of directors", "Maximum number of directors"
'''
FIELDS = [
    "Business number (BN)",
    "Corporation number"
    "City/town",
    "Province/territory",
]

OUTPUT_FILE = "active_business_corps.csv"

if os.path.exists(OUTPUT_FILE):
    shutil.copy2(OUTPUT_FILE, f"old_{OUTPUT_FILE}")

LIMIT = 32000
offset = 0

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()

    while True:
        payload = {
            "resource_id": RESOURCE_ID,
            "fields": FIELDS,
            "limit": LIMIT,
            "offset": offset,
        }

        response = requests.post(API_URL, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            raise RuntimeError(data)

        records = data["result"]["records"]

        if not records:
            break

        for record in records:
            writer.writerow({
                field: record.get(field, "")
                for field in FIELDS
            })

        print(f"Downloaded {offset + len(records)} rows...")

        offset += len(records)

        if len(records) < LIMIT:
            break

print(f"Done. Saved to {OUTPUT_FILE}")