FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 ANONYMIZED_TELEMETRY=False

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model at build time so the container starts fast.
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction as E; E()(['warmup'])"

COPY app ./app
COPY ui ./ui
COPY evals ./evals
COPY data/docs ./data/docs

EXPOSE 8000
CMD ["sh", "-c", "python -m app.ingest && uvicorn app.api:app --host 0.0.0.0 --port 8000"]
