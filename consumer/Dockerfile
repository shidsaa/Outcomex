FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY consumer.py .
COPY api_server.py .

RUN mkdir -p logs

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/api/system-health')" || exit 1

CMD ["python", "consumer.py"] 