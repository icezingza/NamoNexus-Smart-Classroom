FROM python:3.11-slim

WORKDIR /app

# System deps: gcc/libpq for psycopg2-binary; curl for healthcheck probe
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first — layer cached unless requirements.txt changes
COPY backend/namo_core/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source (knowledge/ excluded via .dockerignore — downloaded from GCS at runtime)
COPY backend/ ./backend/

# Cloud Run injects PORT; default 8000 matches our settings
EXPOSE 8000

# 2 workers matches Cloud Run 2-CPU allocation; override via UVICORN_WORKERS env var
CMD ["sh", "-c", "uvicorn namo_core.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-2}"]
