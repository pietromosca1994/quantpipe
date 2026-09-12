# Build context is the repo root (see docker-compose.yml).
# Hosts the long-lived process that keeps every flow deployment scheduled.
FROM python:3.12-slim

WORKDIR /app

COPY common /app/common
COPY services/ingestion/requirements.txt /app/services/ingestion/requirements.txt
COPY services/prefect_flows/requirements.txt /app/services/prefect_flows/requirements.txt
RUN pip install --no-cache-dir \
    -e /app/common \
    -r /app/services/ingestion/requirements.txt \
    -r /app/services/prefect_flows/requirements.txt

COPY services/ingestion/src /app/services/ingestion/src
COPY services/prefect_flows /app/services/prefect_flows
COPY config /app/config

ENV PYTHONPATH=/app/services/ingestion/src:/app/services/prefect_flows

WORKDIR /app/services/prefect_flows

CMD ["python", "deployments.py"]
