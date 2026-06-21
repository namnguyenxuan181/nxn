import glob
import json
import os
import re

import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@st.cache_data(ttl=300)
def available_dates(domain: str) -> list:
    pattern = os.path.join(DATA_DIR, domain, f"{domain}_*.csv")
    files = glob.glob(pattern)
    dates = []
    for f in files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            dates.append(m.group(1))
    return sorted(dates, reverse=True)


@st.cache_data
def load_interest(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "interest", f"interest_{date}.csv")
    return pd.read_csv(path)


@st.cache_data
def load_stock(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "stock", f"stock_{date}.csv")
    return pd.read_csv(path)


@st.cache_data(ttl=300)
def available_news_dates() -> list:
    pattern = os.path.join(DATA_DIR, "news", "news_*.json")
    files = glob.glob(pattern)
    dates = []
    for f in files:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(f))
        if m:
            dates.append(m.group(1))
    return sorted(dates, reverse=True)


@st.cache_data(ttl=300)
def load_news(date: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, "news", f"news_{date}.json")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["source", "title", "url", "published_at", "description", "summary", "sentiment"])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)
