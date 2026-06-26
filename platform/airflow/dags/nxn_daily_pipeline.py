"""
NXN Daily Pipeline
  1. ingest: scrape → Iceberg raw tables (qua Trino)
  2. transform: dbt run (staging → mart)
  3. test: dbt test
  4. chromadb_sync: embed mart data → ChromaDB cho RAG
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

TRINO_HOST = "trino"
TRINO_PORT = 8080
DATA_DIR   = "/opt/nxn/data"
DBT_DIR    = "/opt/dbt"

default_args = {
    "owner": "nxn",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="nxn_daily_pipeline",
    description="Ingest → dbt transform → ChromaDB sync",
    start_date=datetime(2026, 6, 1),
    schedule="0 18 * * 1-5",   # 18:00 các ngày thường (sau khi thị trường đóng)
    catchup=False,
    default_args=default_args,
    tags=["nxn", "daily"],
) as dag:

    # ── 1. Scrape dữ liệu mới ─────────────────────────────
    scrape = BashOperator(
        task_id="scrape_data",
        bash_command="cd /opt/nxn && python main.py",
    )

    # ── 2. Ingest CSV/JSON → Iceberg ─────────────────────
    ingest = BashOperator(
        task_id="ingest_to_iceberg",
        bash_command=(
            f"python /opt/nxn/platform/scripts/ingest_csv_to_iceberg.py "
            f"--data-dir {DATA_DIR} "
            f"--trino-host {TRINO_HOST} "
            f"--trino-port {TRINO_PORT}"
        ),
    )

    # ── 3. dbt run (staging + mart) ───────────────────────
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"TRINO_HOST={TRINO_HOST} TRINO_PORT={TRINO_PORT} "
            f"dbt run --profiles-dir {DBT_DIR} --project-dir {DBT_DIR} --no-version-check"
        ),
    )

    # ── 4. dbt test ───────────────────────────────────────
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {DBT_DIR} && "
            f"TRINO_HOST={TRINO_HOST} TRINO_PORT={TRINO_PORT} "
            f"dbt test --profiles-dir {DBT_DIR} --project-dir {DBT_DIR} --no-version-check"
        ),
    )

    # ── 5. Sync mart → ChromaDB cho RAG ──────────────────
    def sync_chromadb(**ctx):
        """Lấy dữ liệu từ Trino mart và index vào ChromaDB."""
        import chromadb
        import trino as trino_lib

        chroma = chromadb.HttpClient(host="chromadb", port=8000)
        collection = chroma.get_or_create_collection("nxn_stock_context")

        conn = trino_lib.dbapi.connect(
            host=TRINO_HOST, port=TRINO_PORT, user="airflow",
            catalog="iceberg", schema="mart", http_scheme="http",
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT symbol, trade_date, close_price, change_pct, market_sentiment
            FROM iceberg.mart.mart_stock_daily
            WHERE trade_date >= CURRENT_DATE - INTERVAL '7' DAY
            ORDER BY trade_date DESC, symbol
        """)
        rows = cur.fetchall()

        docs, ids, metas = [], [], []
        for symbol, date, close, chg, sent in rows:
            doc = (
                f"Cổ phiếu {symbol} ngày {date}: "
                f"giá đóng cửa {close:,} VND, "
                f"thay đổi {chg:+.2f}%, "
                f"sentiment thị trường {sent:.2f}"
            )
            docs.append(doc)
            ids.append(f"{symbol}_{date}")
            metas.append({"symbol": symbol, "date": str(date)})

        if docs:
            collection.upsert(documents=docs, ids=ids, metadatas=metas)
            print(f"ChromaDB: upserted {len(docs)} documents")

    chromadb_sync = PythonOperator(
        task_id="chromadb_sync",
        python_callable=sync_chromadb,
    )

    # ── Pipeline order ─────────────────────────────────────
    scrape >> ingest >> dbt_run >> dbt_test >> chromadb_sync
