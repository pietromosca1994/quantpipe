# Build context is the repo root (see docker-compose.yml), so this can reach common/.
FROM python:3.12-slim

WORKDIR /app

COPY common /app/common
COPY services/ingestion/requirements.txt /app/services/ingestion/requirements.txt
RUN pip install --no-cache-dir -e /app/common -r /app/services/ingestion/requirements.txt

COPY services/ingestion/src /app/services/ingestion/src
COPY config /app/config

ENV PYTHONPATH=/app/services/ingestion/src

WORKDIR /app/services/ingestion

CMD ["python", "-m", "ingestion.flow"]
