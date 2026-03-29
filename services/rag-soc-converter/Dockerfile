FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt setup.py ./
COPY src/ ./src/

RUN pip install --no-cache-dir -r requirements.txt && pip install -e .

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["hdx-converter-api", "--host", "0.0.0.0", "--port", "8080"]