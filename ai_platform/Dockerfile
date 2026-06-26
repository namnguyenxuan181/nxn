FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir trino==0.328.0 chromadb-client

COPY . .

CMD ["uvicorn", "ai_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
