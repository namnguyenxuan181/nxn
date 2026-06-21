import os
from datetime import date as _date

import pandas as pd
import streamlit as st

from web.data_loader import (
    available_dates,
    available_news_dates,
    load_interest,
    load_news,
    load_stock,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

st.set_page_config(page_title="NXN Dashboard", layout="wide")
st.title("📊 NXN Dashboard")

tab1, tab2, tab3 = st.tabs(["💰 Interest Rates", "📈 Stock Prices", "📰 News"])

# ── Interest Rates ────────────────────────────────────────────────────────────
with tab1:
    dates = available_dates("interest")
    if not dates:
        st.info("No data available yet. Run main.py first.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            date = st.selectbox("Date", dates, key="interest_date")
        with col2:
            channel = st.selectbox("Channel", ["All", "counter", "online"], key="interest_channel")

        df = load_interest(date)
        if channel != "All":
            df = df[df["channel"] == channel]

        display = df.drop(columns=["date"]).rename(columns={
            "bank": "Bank", "channel": "Channel",
            "rate_1m": "1m %", "rate_3m": "3m %", "rate_6m": "6m %",
            "rate_12m": "12m %", "rate_18m": "18m %",
            "rate_24m": "24m %", "rate_36m": "36m %",
        })

        rate_cols = ["1m %", "3m %", "6m %", "12m %", "18m %", "24m %", "36m %"]
        col_config = {
            col: st.column_config.ProgressColumn(col, min_value=0, max_value=10, format="%.2f %%")
            for col in rate_cols
        }
        st.dataframe(display, column_config=col_config, use_container_width=True, hide_index=True)

# ── Stock Prices ──────────────────────────────────────────────────────────────
with tab2:
    dates = available_dates("stock")
    if not dates:
        st.info("No data available yet. Run main.py first.")
    else:
        col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
        with col1:
            date = st.selectbox("Date", dates, key="stock_date")
        with col2:
            search = st.text_input("Search symbol", key="stock_search")
        with col3:
            sort_col = st.selectbox(
                "Sort by", ["symbol", "open", "high", "low", "close", "volume"],
                key="stock_sort",
            )
        with col4:
            order = st.selectbox("Order", ["Descending", "Ascending"], key="stock_order")

        df = load_stock(date)
        if search:
            df = df[df["symbol"].str.contains(search.upper(), na=False)]
        df = df.sort_values(sort_col, ascending=(order == "Ascending"))

        display = df.drop(columns=["date"]).rename(columns={
            "symbol": "Symbol", "open": "Open", "high": "High",
            "low": "Low", "close": "Close", "volume": "Volume",
        })
        st.dataframe(
            display.style.format({
                "Open": "{:,.0f}", "High": "{:,.0f}",
                "Low": "{:,.0f}", "Close": "{:,.0f}", "Volume": "{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

# ── News ──────────────────────────────────────────────────────────────────────
with tab3:
    from news.keywords import KEYWORDS

    news_dates = available_news_dates()
    col1, col2 = st.columns([3, 1])
    with col1:
        if news_dates:
            news_date = st.selectbox("Date", news_dates, key="news_date")
        else:
            news_date = _date.today().strftime("%Y-%m-%d")
            st.info("No news yet. Click Fetch & Analyze.")
    with col2:
        st.write("")
        fetch_btn = st.button("🔄 Fetch & Analyze", key="news_fetch")

    if fetch_btn:
        label = "Fetching and analyzing news…" if os.environ.get("ANTHROPIC_API_KEY") else "Fetching news (no API key — summary/sentiment will be empty)…"
        with st.spinner(label):
            from news.repositories.json_repo import JSONNewsRepository
            from news.runner import NewsRunner
            from news.scrapers.cafef import CafefScraper
            from news.scrapers.vnexpress import VnExpressScraper
            from news.scrapers.vietstock import VietstockScraper
            NewsRunner(
                [VnExpressScraper(), CafefScraper(), VietstockScraper()],
                JSONNewsRepository(data_dir=os.path.join(DATA_DIR, "news")),
            ).run(target_date=news_date)
            st.cache_data.clear()
            st.rerun()

    news_dates = available_news_dates()
    if news_dates:
        df = load_news(news_date)

        if df.empty:
            st.info("No articles for this date.")
        else:
            st.caption(f"Keywords: {', '.join(KEYWORDS[:8])} …")

            def _matches(row: pd.Series) -> bool:
                text = (str(row.get("title", "")) + " " + str(row.get("description", ""))).lower()
                return any(kw.lower() in text for kw in KEYWORDS)

            df["matched"] = df.apply(_matches, axis=1)
            df["sentiment_icon"] = df["sentiment"].map({"positive": "🟢", "negative": "🔴", "neutral": "⚪"}).fillna("⚪")
            df["datetime"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce") \
                .dt.tz_convert("Asia/Ho_Chi_Minh").dt.strftime("%Y-%m-%d %H:%M")
            df = df.sort_values(["matched", "published_at"], ascending=[False, False])

            rows_html = ""
            for _, row in df.iterrows():
                bg = "background-color:#fff9c4;" if row["matched"] else ""
                title_html = f'<a href="{row["url"]}" target="_blank">{row["title"]}</a>'
                rows_html += (
                    f'<tr style="{bg}">'
                    f'<td style="white-space:nowrap;padding:4px 8px;">{row["source"]}</td>'
                    f'<td style="padding:4px 8px;">{title_html}</td>'
                    f'<td style="text-align:center;padding:4px 8px;">{row["sentiment_icon"]}</td>'
                    f'<td style="white-space:nowrap;padding:4px 8px;">{row["datetime"]}</td>'
                    f'</tr>'
                )
            st.html(
                f'<table style="width:100%;border-collapse:collapse;font-size:14px;">'
                f'<thead><tr style="border-bottom:2px solid #ddd;">'
                f'<th style="text-align:left;padding:4px 8px;">Source</th>'
                f'<th style="text-align:left;padding:4px 8px;">Title</th>'
                f'<th style="padding:4px 8px;">📊</th>'
                f'<th style="text-align:left;padding:4px 8px;">Time</th>'
                f'</tr></thead>'
                f'<tbody>{rows_html}</tbody>'
                f'</table>'
            )

            matched = df[df["matched"]]
            if not matched.empty:
                st.subheader("Matched Articles — AI Summaries")
                for _, row in matched.iterrows():
                    icon = "🟢" if row["sentiment"] == "positive" else "🔴" if row["sentiment"] == "negative" else "⚪"
                    with st.expander(f"{icon} {row['title']}"):
                        st.write(row["summary"] if row["summary"] else "_No summary available._")
                        st.markdown(f"[Read full article]({row['url']})")
