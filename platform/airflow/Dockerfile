FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir \
    dbt-core==1.8.3 \
    dbt-trino==1.8.1 \
    trino==0.328.0 \
    pyiceberg[hive,s3]==0.7.1 \
    pyarrow==16.1.0 \
    pandas==2.2.2 \
    boto3==1.34.0 \
    chromadb-client==0.5.0
