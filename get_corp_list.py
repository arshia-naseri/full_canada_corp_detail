import os
import shutil
import requests
import pandas as pd

API_URL = "https://demo.datashades.com/api/3/action/datastore_search"

RESOURCE_ID = "7b6dd154-aa04-46ce-8880-ce4a5fa0a680"  # Active business corporations

''' 
    The following are the columns:
    "Corporation number", "Business number (BN)", "Corporate name - form 1",
    "Corporate name - form 2", "Governing legislation", "Status", "Anniversary date", "Year of last annual filing",
    "Date of last annual meeting", "Street", "Street 2", "City/town", "Province/territory", "Country", "Postal code",
    "Minimum number of directors", "Maximum number of directors"
'''
FIELDS = [
    "Business number (BN)",
    "Corporation number",
    "City/town",
    "Province/territory",
]

OUTPUT_FILE = "active_business_corps.csv"
BACKUP_FILE = f"old_{OUTPUT_FILE}"
DELTA_FILE = f"delta_{OUTPUT_FILE}"

if os.path.exists(OUTPUT_FILE):
    shutil.copy2(OUTPUT_FILE, BACKUP_FILE)

LIMIT = 32000
offset = 0
chunks = []

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

    chunks.append(pd.DataFrame(records)[FIELDS])
    offset += len(records)
    print(f"Downloaded {offset} rows...")

    if len(records) < LIMIT:
        break

df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=FIELDS)
df["Province/territory"] = df["Province/territory"].str.upper()
df["City/town"] = df["City/town"].str.title()
df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
print(f"Done. Saved to {OUTPUT_FILE}")

if os.path.exists(BACKUP_FILE):
    old_df = pd.read_csv(BACKUP_FILE, dtype=str).fillna("")
    new_df = df.astype(str).fillna("")

    added = new_df.merge(old_df, on=FIELDS, how="left", indicator=True).query('_merge == "left_only"').drop(columns="_merge").assign(change="added")
    removed = old_df.merge(new_df, on=FIELDS, how="left", indicator=True).query('_merge == "left_only"').drop(columns="_merge").assign(change="removed")

    delta_df = pd.concat([added, removed], ignore_index=True)[["change"] + FIELDS]
    delta_df.to_csv(DELTA_FILE, index=False, encoding="utf-8")

    print(f"\nTotal rows #: {df.shape[0]}")
    print(f"New rows #:   {added.shape[0]}")
    print(f"Delta rows #: {delta_df.shape[0]}")
else:
    print("No backup found. Skipping delta.")
    print(f"\nTotal rows #: {df.shape[0]}")
