import pandas as pd
from corp_list import CorpListFetcher
from corp_detail import CorpDetailFetcher

path, is_delta = CorpListFetcher().run()

if is_delta:
    df = pd.read_csv(path, dtype=str).fillna("")
    added = df.loc[df["change"] == "added", "Corporation number"].tolist()
    removed = df.loc[df["change"] == "removed", "Corporation number"].tolist()
    fetcher = CorpDetailFetcher(added)
    fetcher.append()        # insert added corps only
    fetcher.remove(removed) # drop removed corps from jsonl
else:
    ids = pd.read_csv(path, dtype=str)["Corporation number"].tolist()
    CorpDetailFetcher(ids).run()
