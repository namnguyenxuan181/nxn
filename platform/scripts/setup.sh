#!/usr/bin/env bash
# Setup script — chạy lần đầu sau khi docker compose up

set -e
cd "$(dirname "$0")/.."

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " NXN Data Platform — First-time Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Copy .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[1/5] .env created from .env.example"
else
  echo "[1/5] .env already exists"
fi

# 2. Khởi động services
echo "[2/5] Starting platform services..."
docker compose up -d minio nessie trino postgres
echo "  Waiting 30s for services to initialize..."
sleep 30

# 3. Ingest dữ liệu CSV → Iceberg
echo "[3/5] Ingesting existing CSV/JSON data into Iceberg..."
docker compose run --rm -e TRINO_HOST=trino airflow \
  python /opt/nxn/platform/scripts/ingest_csv_to_iceberg.py \
  --data-dir /opt/nxn/data --trino-host trino --trino-port 8080

# 4. Chạy dbt
echo "[4/5] Running dbt models..."
docker compose run --rm \
  -e TRINO_HOST=trino -e TRINO_PORT=8080 \
  airflow bash -c "cd /opt/dbt && dbt deps && dbt run --profiles-dir /opt/dbt --project-dir /opt/dbt"

# 5. Khởi động tất cả services
echo "[5/5] Starting remaining services..."
docker compose up -d

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Platform ready!"
echo ""
echo "  MinIO     → http://localhost:9001   (minioadmin/minioadmin)"
echo "  Trino     → http://localhost:8080"
echo "  Airflow   → http://localhost:8082   (admin/admin)"
echo "  Superset  → http://localhost:8088   (admin/admin)"
echo "  AI Plat.  → http://localhost:8300"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
