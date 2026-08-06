FROM python:3.12-slim

WORKDIR /app

# System deps kept minimal; wheels cover most Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY config/ config/
COPY core/ core/
COPY sources/ sources/
COPY templates/ templates/
COPY static/ static/
COPY profiles/ profiles/

# SQLite lives on a volume; credentials stay out of the image
ENV PORT=8000 \
    DB_PATH=/data/jobs.db \
    PYTHONUNBUFFERED=1

RUN mkdir -p /data \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# Bind all interfaces inside the container so published ports work.
# Access from the host as http://localhost:{PORT}
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
