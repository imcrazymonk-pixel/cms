FROM docker:27-cli

# docker:27-cli is Alpine-based and already ships the Docker CLI + compose plugin.
RUN apk add --no-cache \
        python3 \
        py3-pip \
        age \
        tar \
        gzip \
        zstd \
        tzdata \
        curl \
        ca-certificates

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY src ./src

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["python3", "-m", "src.main"]
