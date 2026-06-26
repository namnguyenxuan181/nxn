"""
Ingest dữ liệu từ CSV/JSON → Iceberg tables thông qua Trino.
Chạy: python ingest_csv_to_iceberg.py --data-dir ../../data --trino-host localhost
"""

import argparse
import glob
import json
import os
import sys
import time

import pandas as pd
import trino

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--data-dir",   default=os.environ.get("DATA_DIR", "../../data"))
parser.add_argument("--trino-host", default=os.environ.get("TRINO_HOST", "localhost"))
parser.add_argument("--trino-port", type=int, default=int(os.environ.get("TRINO_PORT", 8080)))
args = parser.parse_args()

DATA_DIR = args.data_dir
TRINO_HOST = args.trino_host
TRINO_PORT = args.trino_port


# ── Trino connection ──────────────────────────────────────────────────────────
def connect():
    return trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user="ingest",
        catalog="iceberg",
        schema="raw",
        http_scheme="http",
    )


def execute(cur, sql: str, desc: str = ""):
    if desc:
        print(f"  → {desc}")
    cur.execute(sql)
    try:
        cur.fetchall()
    except Exception:
        pass


def executemany(cur, sql: str, rows: list, batch: int = 500):
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        values = ", ".join(
            "(" + ", ".join(("NULL" if v is None else f"'{str(v).replace(chr(39), chr(39)*2)}'") for v in row) + ")"
            for row in chunk
        )
        cur.execute(sql.replace("__VALUES__", values))
        try:
            cur.fetchall()
        except Exception:
            pass
        print(f"    inserted {min(i + batch, len(rows))}/{len(rows)} rows", end="\r")
    print()


# ── Schema + Table setup ──────────────────────────────────────────────────────
def setup_schema(cur):
    execute(cur, """
        CREATE SCHEMA IF NOT EXISTS iceberg.raw
        WITH (location = 's3://warehouse/raw/')
    """, "create schema raw")

    execute(cur, """
        CREATE TABLE IF NOT EXISTS iceberg.raw.stock_prices (
            date      VARCHAR,
            symbol    VARCHAR,
            open      BIGINT,
            high      BIGINT,
            low       BIGINT,
            close     BIGINT,
            volume    BIGINT
        ) WITH (
            format = 'PARQUET',
            location = 's3://warehouse/raw/stock_prices/'
        )
    """, "create table stock_prices")

    execute(cur, """
        CREATE TABLE IF NOT EXISTS iceberg.raw.news (
            source       VARCHAR,
            title        VARCHAR,
            url          VARCHAR,
            published_at VARCHAR,
            description  VARCHAR,
            sentiment    VARCHAR
        ) WITH (
            format = 'PARQUET',
            location = 's3://warehouse/raw/news/'
        )
    """, "create table news")

    execute(cur, """
        CREATE TABLE IF NOT EXISTS iceberg.raw.interest_rates (
            bank       VARCHAR,
            channel    VARCHAR,
            rate_3m    DOUBLE,
            rate_6m    DOUBLE,
            rate_12m   DOUBLE,
            rate_24m   DOUBLE,
            fetched_at VARCHAR
        ) WITH (
            format = 'PARQUET',
            location = 's3://warehouse/raw/interest_rates/'
        )
    """, "create table interest_rates")


# ── Ingest functions ──────────────────────────────────────────────────────────
def ingest_stocks(cur):
    files = sorted(glob.glob(os.path.join(DATA_DIR, "stock", "stock_*.csv")))
    if not files:
        print("  ! No stock CSV files found")
        return

    # Truncate để ingest lại toàn bộ (demo)
    execute(cur, "DELETE FROM iceberg.raw.stock_prices WHERE 1=1", "truncate stock_prices")

    total = 0
    for f in files:
        date_str = os.path.basename(f).replace("stock_", "").replace(".csv", "")
        df = pd.read_csv(f)
        df = df[["symbol", "open", "high", "low", "close", "volume"]].copy()
        df = df.dropna(subset=["symbol", "close"])
        df["date"] = date_str
        df = df[["date", "symbol", "open", "high", "low", "close", "volume"]]
        rows = [tuple(str(v) if pd.notna(v) else None for v in row) for row in df.itertuples(index=False)]
        if rows:
            executemany(cur, "INSERT INTO iceberg.raw.stock_prices VALUES __VALUES__", rows)
            total += len(rows)
        print(f"  {date_str}: {len(rows)} rows")
    print(f"  Total stock rows: {total}")


def ingest_news(cur):
    files = sorted(glob.glob(os.path.join(DATA_DIR, "news", "news_*.json")))
    if not files:
        print("  ! No news JSON files found")
        return

    execute(cur, "DELETE FROM iceberg.raw.news WHERE 1=1", "truncate news")

    total = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            articles = json.load(fh)
        rows = []
        for a in articles:
            rows.append((
                a.get("source"),
                a.get("title"),
                a.get("url"),
                a.get("published_at"),
                a.get("description"),
                a.get("sentiment"),
            ))
        if rows:
            executemany(cur, "INSERT INTO iceberg.raw.news VALUES __VALUES__", rows)
            total += len(rows)
        print(f"  {os.path.basename(f)}: {len(rows)} articles")
    print(f"  Total news rows: {total}")


def ingest_interest_rates(cur):
    files = sorted(glob.glob(os.path.join(DATA_DIR, "interest", "interest_*.csv")))
    if not files:
        print("  ! No interest CSV files found")
        return

    execute(cur, "DELETE FROM iceberg.raw.interest_rates WHERE 1=1", "truncate interest_rates")

    for f in files:
        date_str = os.path.basename(f).replace("interest_", "").replace(".csv", "")
        df = pd.read_csv(f)
        rows = []
        for _, row in df.iterrows():
            rows.append((
                row.get("bank"), row.get("channel"),
                row.get("rate_3m"), row.get("rate_6m"),
                row.get("rate_12m"), row.get("rate_24m"),
                date_str,
            ))
        if rows:
            executemany(cur, "INSERT INTO iceberg.raw.interest_rates VALUES __VALUES__", rows)
        print(f"  {date_str}: {len(rows)} rows")


# ── Main ──────────────────────────────────────────────────────────────────────
def wait_for_trino(max_retries: int = 20):
    print(f"Waiting for Trino at {TRINO_HOST}:{TRINO_PORT} ...")
    for i in range(max_retries):
        try:
            conn = connect()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchall()
            print("Trino is ready.")
            return
        except Exception:
            time.sleep(5)
    print("ERROR: Trino not available after retries", file=sys.stderr)
    sys.exit(1)


def main():
    wait_for_trino()
    conn = connect()
    cur = conn.cursor()

    print("\n[1/4] Setting up schemas and tables...")
    setup_schema(cur)

    print("\n[2/4] Ingesting stock prices...")
    ingest_stocks(cur)

    print("\n[3/4] Ingesting news...")
    ingest_news(cur)

    print("\n[4/4] Ingesting interest rates...")
    ingest_interest_rates(cur)

    print("\nIngest complete!")


if __name__ == "__main__":
    main()
