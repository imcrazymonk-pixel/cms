# HexaVeil CMS Backend — Dockerfile
# Based on Remnawave's pattern (python:3.11-slim)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY web/backend/requirements.txt /app/web/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/web/backend/requirements.txt

# Copy application code
COPY web/backend/ /app/web/backend/
COPY .env /app/.env

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--log-level", "info"]