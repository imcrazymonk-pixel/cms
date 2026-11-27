#!/usr/bin/env bash
# HexaVeil backup agent installer.
# Usage:
#   curl -sSL https://hexaveil.xyz/api/backup-agent/v1/install.sh | bash -s -- \
#     --url https://hexaveil.xyz --host-id <uuid> --token <token>
set -euo pipefail

INSTALL_DIR="/opt/hexaveil-backup-agent"
DEFAULT_IMAGE="ghcr.io/hexaveil/backup-agent:latest"
MIN_DISK_MB=2048

AGENT_URL=""
HOST_ID=""
TOKEN=""
ROLE="server"
IMAGE="${AGENT_IMAGE:-$DEFAULT_IMAGE}"
IMAGE_TARBALL=""

log()  { printf '\033[36m[agent]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[agent]\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Options:
  --url       CMS base URL (https://hexaveil.xyz)
  --host-id   Host UUID from the CMS
  --token     Agent token from the CMS
  --role      server|node (informational)
  --image     Override agent image
  --image-tarball  URL or path to a `docker save` archive of the agent image
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)     AGENT_URL="${2:-}"; shift 2 ;;
    --host-id) HOST_ID="${2:-}"; shift 2 ;;
    --token)   TOKEN="${2:-}"; shift 2 ;;
    --role)    ROLE="${2:-server}"; shift 2 ;;
    --image)   IMAGE="${2:-}"; shift 2 ;;
    --image-tarball) IMAGE_TARBALL="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
done

[[ -n "$AGENT_URL" && -n "$HOST_ID" && -n "$TOKEN" ]] || { usage; fail "--url, --host-id and --token are required"; }

# A node cannot reach the CMS via loopback; catching it here saves a confusing
# curl/SSL error and a half-installed agent.
case "$AGENT_URL" in
  *://127.0.0.1*|*://localhost*) fail "--url must be reachable from this server (got ${AGENT_URL}); use the public CMS address, e.g. https://hexaveil.xyz" ;;
esac
[[ "$(id -u)" -eq 0 ]] || fail "run as root"

command -v docker >/dev/null 2>&1 || fail "docker is not installed"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is not available"
command -v curl >/dev/null 2>&1 || fail "curl is not installed"

AVAILABLE_MB=$(df -Pm / | awk 'NR==2 {print $4}')
if [[ -n "$AVAILABLE_MB" && "$AVAILABLE_MB" -lt "$MIN_DISK_MB" ]]; then
  fail "not enough disk space: ${AVAILABLE_MB}MB available, ${MIN_DISK_MB}MB required"
fi

if [[ -f "$INSTALL_DIR/.env" ]]; then
  log "existing installation found, updating configuration"
fi

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

umask 077
cat > .env <<EOF
AGENT_URL=${AGENT_URL}
AGENT_HOST_ID=${HOST_ID}
AGENT_TOKEN=${TOKEN}
AGENT_SPOOL_DIR=/var/lib/hexaveil-agent
AGENT_CONCURRENCY=1
AGENT_TZ=${TZ:-UTC}
AGENT_HOST_MODE=false
AGENT_HOST_PREFIX=/host
AGENT_LOG_LEVEL=info
AGENT_IMAGE=${IMAGE}
AGENT_ROLE=${ROLE}
EOF
chmod 600 .env

cat > docker-compose.yml <<'YAML'
name: hexaveil-backup-agent

services:
  agent:
    image: ${AGENT_IMAGE:-ghcr.io/hexaveil/backup-agent:latest}
    container_name: hexaveil-backup-agent
    restart: unless-stopped
    env_file: .env
    pid: host
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - type: bind
        source: /opt/remnawave
        target: /host/opt/remnawave
        read_only: true
        bind:
          create_host_path: false
      - type: bind
        source: /opt/remnanode
        target: /host/opt/remnanode
        read_only: true
        bind:
          create_host_path: false
      - type: bind
        source: /srv/cabinet
        target: /host/srv/cabinet
        read_only: true
        bind:
          create_host_path: false
      - agent_spool:/var/lib/hexaveil-agent
    healthcheck:
      test: ["CMD", "python3", "-c", "import os,sys;sys.exit(0 if os.path.exists('/tmp/agent.ready') else 1)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "3"

volumes:
  agent_spool:
YAML

if [[ -n "$IMAGE_TARBALL" ]]; then
  log "loading image from ${IMAGE_TARBALL}"
  TMP_TAR="$(mktemp /tmp/hexaveil-agent-image.XXXXXX.tar)"
  if [[ "$IMAGE_TARBALL" == http://* || "$IMAGE_TARBALL" == https://* ]]; then
    curl -fsSL "$IMAGE_TARBALL" -o "$TMP_TAR" || fail "cannot download image archive"
  else
    cp "$IMAGE_TARBALL" "$TMP_TAR" || fail "cannot read image archive"
  fi
  docker load -i "$TMP_TAR" || fail "docker load failed"
  rm -f "$TMP_TAR"
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  log "pulling ${IMAGE}"
  docker compose pull --quiet || true
fi

# No registry? The CMS can serve a `docker save` archive.
if ! docker image inspect "$IMAGE" >/dev/null 2>&1 && [[ -z "$IMAGE_TARBALL" ]]; then
  log "trying agent image archive from ${AGENT_URL%/}/api/backup-agent/v1/image"
  TMP_TAR="$(mktemp /tmp/hexaveil-agent-image.XXXXXX.tar)"
  if curl -fsSL "${AGENT_URL%/}/api/backup-agent/v1/image" -o "$TMP_TAR"; then
    docker load -i "$TMP_TAR" && rm -f "$TMP_TAR" || rm -f "$TMP_TAR"
  else
    rm -f "$TMP_TAR"
    log "no image archive published on the CMS"
  fi
fi

docker image inspect "$IMAGE" >/dev/null 2>&1 || fail "agent image ${IMAGE} is not available.
Publish it to a registry, or build it and put the archive on the CMS (backup-agent/agent-image.tar),
or pass --image-tarball /path/agent.tar."

log "starting agent"
docker compose up -d

sleep 3
if docker compose ps --format json | grep -q '"State":"running"'; then
  log "agent is running"
  log "logs: docker logs -f hexaveil-backup-agent"
else
  log "agent did not report running yet — check: docker compose -f ${INSTALL_DIR}/docker-compose.yml logs"
fi

log "done. host-id=${HOST_ID} role=${ROLE}"
