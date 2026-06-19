import glob
import os
import re

import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@st.cache_data
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
