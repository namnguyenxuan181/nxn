import streamlit as st
from web.data_loader import available_dates, load_interest, load_stock

st.set_page_config(page_title="NXN Dashboard", layout="wide")
st.title("📊 NXN Dashboard")

tab1, tab2 = st.tabs(["💰 Interest Rates", "📈 Stock Prices"])

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
        st.dataframe(
            display,
            column_config=col_config,
            use_container_width=True,
            hide_index=True,
        )

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
                "Low": "{:,.0f}", "Close": "{:,.0f}",
                "Volume": "{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
