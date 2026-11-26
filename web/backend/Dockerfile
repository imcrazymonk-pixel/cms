# HexaVeil CMS Backend — Dockerfile
# Based on Remnawave's pattern (python:3.11-slim)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    tar \
    gzip \
    zstd \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY web/backend/requirements.txt /app/web/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/web/backend/requirements.txt

# Copy application code
COPY web/backend/ /app/web/backend/
# Agent installer is served by /api/backup-agent/v1/install.sh
COPY backup-agent/ /app/backup-agent/
# NOTE: .env is deliberately NOT copied into the image. Runtime config comes
# from `env_file: .env` in compose; baking secrets into the image breaks fresh
# clones (and `.dockerignore` also excludes .env).

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
# Часовой пояс по умолчанию (переопределяется TZ из .env). Нужен tzdata выше,
# иначе TZ игнорируется и время логов остаётся UTC.
ENV TZ=Europe/Moscow

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--log-level", "info"]