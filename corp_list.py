import os
import shutil
import requests
import pandas as pd


class CorpListFetcher:
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
    BACKUP_FILE = f"old_active_business_corps.csv"
    DELTA_FILE = f"delta_active_business_corps.csv"
    LIMIT = 32000

    def run(self) -> tuple[str, bool]:
        """
        Fetch full corp list, write OUTPUT_FILE, compute delta if backup exists.
        Returns (DELTA_FILE, True) if delta generated, else (OUTPUT_FILE, False).
        """
        if os.path.exists(self.OUTPUT_FILE):
            shutil.copy2(self.OUTPUT_FILE, self.BACKUP_FILE)

        offset = 0
        chunks = []

        while True:
            payload = {
                "resource_id": self.RESOURCE_ID,
                "fields": self.FIELDS,
                "limit": self.LIMIT,
                "offset": offset,
            }

            response = requests.post(self.API_URL, json=payload, timeout=60)
            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                raise RuntimeError(data)

            records = data["result"]["records"]

            if not records:
                break

            chunks.append(pd.DataFrame(records)[self.FIELDS])
            offset += len(records)
            print(f"Downloaded {offset} rows...")

            if len(records) < self.LIMIT:
                break

        df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=self.FIELDS)
        df["Province/territory"] = df["Province/territory"].str.upper()
        df["City/town"] = df["City/town"].str.title()
        df.to_csv(self.OUTPUT_FILE, index=False, encoding="utf-8")
        print(f"Done. Saved to {self.OUTPUT_FILE}")

        if os.path.exists(self.BACKUP_FILE):
            old_df = pd.read_csv(self.BACKUP_FILE, dtype=str).fillna("")
            new_df = df.astype(str).fillna("")

            added = new_df.merge(old_df, on=self.FIELDS, how="left", indicator=True).query('_merge == "left_only"').drop(columns="_merge").assign(change="added")
            removed = old_df.merge(new_df, on=self.FIELDS, how="left", indicator=True).query('_merge == "left_only"').drop(columns="_merge").assign(change="removed")

            delta_df = pd.concat([added, removed], ignore_index=True)[["change"] + self.FIELDS]
            delta_df.to_csv(self.DELTA_FILE, index=False, encoding="utf-8")

            print(f"\nTotal rows #: {df.shape[0]}")
            print(f"New rows #:   {added.shape[0]}")
            print(f"Delta rows #: {delta_df.shape[0]}")

            return self.DELTA_FILE, True
        else:
            print("No backup found. Skipping delta.")
            print(f"\nTotal rows #: {df.shape[0]}")
            return self.OUTPUT_FILE, False


if __name__ == "__main__":
    CorpListFetcher().run()
