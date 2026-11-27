#!/usr/bin/env bash
# shellcheck shell=bash
# ─────────────────────────────────────────────────────────────────────────────
# HexaVeil CMS — one-command installer.
#
# Two modes:
#   1. run from a cloned checkout:   sudo bash deploy/install.sh
#   2. piped from the internet:      curl -fsSL .../install.sh | sudo bash -s -- ...
#
# In curl mode there is no script directory, so the repository is cloned into
# INSTALL_DIR (default /opt/hexaveil-cms). Interactive prompts are read from
# /dev/tty, because stdin carries the script itself.
#
# Idempotent: existing secrets in .env are preserved, migrations are tracked by
# a ledger, and the admin password is not rotated without --reset-admin-password.
#
# Requires bash 4+, docker + docker compose, curl, git (clone mode), openssl.
# No jq / yq / getopt dependency.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

MANAGED_MARKER="# managed by hexaveil install.sh"

# ── defaults (flags/env override) ────────────────────────────────────────────
SITE_DOMAIN="${SITE_DOMAIN-}"
ADMIN_DOMAIN="${ADMIN_DOMAIN-}"
ACME_EMAIL="${ACME_EMAIL-}"
ADMIN_EMAIL="${ADMIN_EMAIL-}"
ADMIN_LOGIN="${ADMIN_LOGIN-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD-}"
SITE_NAME="${SITE_NAME-}"
ORIGIN_REPO="${HEXAVEIL_REPO_URL-https://github.com/imcrazymonk-pixel/cms.git}"
INSTALL_DIR="${INSTALL_DIR:-/opt/hexaveil-cms}"

NON_INTERACTIVE=0
BEHIND_PROXY=0
ADOPT_EXISTING=0
RESET_ADMIN_PASSWORD=0
RECONFIGURE_DOMAINS=0
NO_INSTALL_DOCKER=0
DRY_RUN=0

SITE_NAME_EXPLICIT=0
ADMIN_LOGIN_EXPLICIT=0
if [ -n "${SITE_NAME-}" ]; then SITE_NAME_EXPLICIT=1; fi
if [ -n "${ADMIN_LOGIN-}" ]; then ADMIN_LOGIN_EXPLICIT=1; fi

REPO_ROOT=""
INSTALL_ROOT=""
ENV_FILE=""
ENV_EXISTED=0
HAVE_DOCKER=0
TTY_OK=0
ANSWER=""
PASSWORD_GENERATED=0
PASSWORD_APPLIED=0
PRINT_PASSWORD=0
CREDENTIALS_FILE=""
HEALTH_LINE="not checked"
ENV_TMP=""

# ── output helpers ───────────────────────────────────────────────────────────
log()  { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Surface the failing line instead of exiting silently on `set -e`.
trap 'printf "ERROR: install.sh failed at line %s (exit %s)\n" "$LINENO" "$?" >&2' ERR

cleanup() {
    if [ -n "$ENV_TMP" ] && [ -f "$ENV_TMP" ]; then rm -f "$ENV_TMP" || true; fi
}
trap cleanup EXIT

usage() {
    cat <<'USAGE'
HexaVeil CMS — one-command installer

Usage:
  sudo bash deploy/install.sh [OPTIONS]
  curl -fsSL <raw-url>/deploy/install.sh | sudo bash -s -- [OPTIONS]

Options (env var in parentheses):
  --site-domain DOMAIN       Public site domain                (SITE_DOMAIN)
  --admin-domain DOMAIN      Admin/API domain                  (ADMIN_DOMAIN)
  --acme-email EMAIL         ACME account email                (ACME_EMAIL)
  --admin-login LOGIN        Admin login, default "admin"      (ADMIN_LOGIN)
  --admin-password PASS      Admin password (else generate)    (ADMIN_PASSWORD)
  --site-name NAME           Site title, default "HexaVeil"    (SITE_NAME)
  --repo URL                 Git URL for curl mode             (HEXAVEIL_REPO_URL)
  --dir PATH                 Install dir for curl mode         (INSTALL_DIR)
  --behind-proxy             Do not bind 80/443; publish 127.0.0.1:3000
                             and generate host-nginx configs
  --proxy=host-nginx         Alias for --behind-proxy
  --adopt-existing           Keep existing secrets/data, dump DB before migrate
  --reset-admin-password     Rotate the existing admin password
  --reconfigure-domains      Allow changing domains on a repeat run
  --no-install-docker        Never install Docker automatically
  --non-interactive          Never ask questions; fail if required flags missing
  --dry-run                  Checks + generate .env + validate Caddyfile only
  --help, -h                 Show this help and exit

Examples:
  sudo bash deploy/install.sh --site-domain example.com \
      --admin-domain admin.example.com --acme-email ops@example.com --non-interactive

  curl -fsSL https://raw.githubusercontent.com/imcrazymonk-pixel/cms/main/deploy/install.sh \
    | sudo bash -s -- --site-domain example.com --admin-domain admin.example.com \
                       --acme-email ops@example.com
USAGE
}

# ── flag parsing ─────────────────────────────────────────────────────────────
need_arg() {
    [ "$#" -ge 2 ] || die "option $1 requires a value"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --site-domain)        need_arg "$@"; SITE_DOMAIN="$2"; shift 2 ;;
        --site-domain=*)      SITE_DOMAIN="${1#*=}"; shift ;;
        --admin-domain)       need_arg "$@"; ADMIN_DOMAIN="$2"; shift 2 ;;
        --admin-domain=*)     ADMIN_DOMAIN="${1#*=}"; shift ;;
        --acme-email)         need_arg "$@"; ACME_EMAIL="$2"; shift 2 ;;
        --acme-email=*)       ACME_EMAIL="${1#*=}"; shift ;;
        --admin-login)        need_arg "$@"; ADMIN_LOGIN="$2"; ADMIN_LOGIN_EXPLICIT=1; shift 2 ;;
        --admin-login=*)      ADMIN_LOGIN="${1#*=}"; ADMIN_LOGIN_EXPLICIT=1; shift ;;
        --admin-password)     need_arg "$@"; ADMIN_PASSWORD="$2"; shift 2 ;;
        --admin-password=*)   ADMIN_PASSWORD="${1#*=}"; shift ;;
        --site-name)          need_arg "$@"; SITE_NAME="$2"; SITE_NAME_EXPLICIT=1; shift 2 ;;
        --site-name=*)        SITE_NAME="${1#*=}"; SITE_NAME_EXPLICIT=1; shift ;;
        --repo)               need_arg "$@"; ORIGIN_REPO="$2"; shift 2 ;;
        --repo=*)             ORIGIN_REPO="${1#*=}"; shift ;;
        --dir)                need_arg "$@"; INSTALL_DIR="$2"; shift 2 ;;
        --dir=*)              INSTALL_DIR="${1#*=}"; shift ;;
        --behind-proxy)       BEHIND_PROXY=1; shift ;;
        --proxy|--proxy=*)
            if [ "$1" = "--proxy" ]; then
                need_arg "$@"
                [ "$2" = "host-nginx" ] || die "--proxy only supports host-nginx"
                BEHIND_PROXY=1; shift 2
            else
                [ "${1#*=}" = "host-nginx" ] || die "--proxy only supports host-nginx"
                BEHIND_PROXY=1; shift
            fi
            ;;
        --adopt-existing)         ADOPT_EXISTING=1; shift ;;
        --reset-admin-password)   RESET_ADMIN_PASSWORD=1; shift ;;
        --reconfigure-domains)    RECONFIGURE_DOMAINS=1; shift ;;
        --no-install-docker)      NO_INSTALL_DOCKER=1; shift ;;
        --non-interactive)        NON_INTERACTIVE=1; shift ;;
        --dry-run)                DRY_RUN=1; shift ;;
        --help|-h)                usage; exit 0 ;;
        *)                        die "unknown option: $1 (see --help)" ;;
    esac
done

# ── tty helpers ──────────────────────────────────────────────────────────────
detect_tty() {
    TTY_OK=0
    if [ -t 0 ]; then
        TTY_OK=1
    elif { : < /dev/tty; } 2>/dev/null; then
        TTY_OK=1
    fi
}

ask_text() {
    if [ "$TTY_OK" != 1 ]; then
        die "no TTY for interactive input. Pass flags (--site-domain, --admin-domain, --acme-email) or use --non-interactive."
    fi
    ANSWER=""
    printf '%s' "$1" >&2
    if [ -t 0 ]; then
        IFS= read -r ANSWER || true
    else
        IFS= read -r ANSWER < /dev/tty || true
    fi
}

ask_secret() {
    if [ "$TTY_OK" != 1 ]; then
        die "no TTY for interactive input. Pass --admin-password or use --non-interactive."
    fi
    ANSWER=""
    printf '%s' "$1" >&2
    if [ -t 0 ]; then
        IFS= read -rs ANSWER || true
    else
        IFS= read -rs ANSWER < /dev/tty || true
    fi
    printf '\n' >&2
}

# ── generic helpers ──────────────────────────────────────────────────────────
env_get() {
    # env_get FILE KEY — value of the last KEY= line (CRLF-tolerant), or empty.
    local file="$1" key="$2" line=""
    if [ -f "$file" ]; then
        line=$(grep -E "^${key}=" "$file" 2>/dev/null | tail -n 1 | tr -d '\r' || true)
    fi
    if [ -n "$line" ]; then printf '%s' "${line#*=}"; fi
}

host_path() {
    # Docker Desktop on Windows needs a native path for -v bind mounts.
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$1"
    else
        printf '%s' "$1"
    fi
}

gen_alnum() {
    command -v openssl >/dev/null 2>&1 || die "openssl is required to generate secrets"
    openssl rand -base64 48 | LC_ALL=C tr -dc 'A-Za-z0-9' | cut -c1-32
}

gen_hex() {
    command -v openssl >/dev/null 2>&1 || die "openssl is required to generate secrets"
    openssl rand -hex 32
}

gen_password() {
    command -v openssl >/dev/null 2>&1 || die "openssl is required to generate the admin password"
    openssl rand -base64 48 | LC_ALL=C tr -dc 'A-Za-z0-9' | cut -c1-24
}

# ── repository resolution ────────────────────────────────────────────────────
resolve_repo() {
    local script_dir=""
    if [ -n "${BASH_SOURCE[0]-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
    fi

    if [ -n "$script_dir" ] && [ -f "$script_dir/compose.install.yml" ]; then
        REPO_ROOT=$(cd "$script_dir/.." && pwd)
        INSTALL_ROOT="$REPO_ROOT"
        log "Repository: $REPO_ROOT (local checkout)"
        return 0
    fi

    # curl | bash mode — no usable script directory.
    command -v git >/dev/null 2>&1 || die "git is required to clone the repository in curl mode"

    if [ -f "$INSTALL_DIR/deploy/compose.install.yml" ]; then
        REPO_ROOT=$(cd "$INSTALL_DIR" && pwd)
        # Existing install: keep the checkout current so install.sh fixes and
        # new migrations actually reach this server. Offline re-runs continue
        # with whatever is on disk.
        if [ -d "$REPO_ROOT/.git" ]; then
            log "Updating existing checkout in $REPO_ROOT"
            git -C "$REPO_ROOT" pull --ff-only \
                || warn "git pull failed; continuing with the current checkout"
        fi
        log "Repository: $REPO_ROOT (existing checkout)"
    elif [ -d "$INSTALL_DIR/.git" ]; then
        log "Updating existing checkout in $INSTALL_DIR"
        git -C "$INSTALL_DIR" pull --ff-only
        REPO_ROOT=$(cd "$INSTALL_DIR" && pwd)
    elif [ -d "$INSTALL_DIR" ] && [ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null || true)" ]; then
        die "$INSTALL_DIR exists and is not a HexaVeil checkout; remove it or use --dir"
    else
        log "Cloning $ORIGIN_REPO into $INSTALL_DIR"
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone "$ORIGIN_REPO" "$INSTALL_DIR"
        REPO_ROOT=$(cd "$INSTALL_DIR" && pwd)
    fi

    [ -f "$REPO_ROOT/deploy/compose.install.yml" ] || die "deploy/compose.install.yml not found in $REPO_ROOT"
    INSTALL_ROOT="$REPO_ROOT"
}

# ── pre-flight checks ────────────────────────────────────────────────────────
check_root() {
    if [ "$DRY_RUN" = 1 ]; then
        warn "dry-run: root check skipped (no system changes will be made)"
        return 0
    fi
    [ "$(id -u)" -eq 0 ] || die "must run as root: sudo bash deploy/install.sh"
}

check_os() {
    local id="" pretty=""
    if [ -r /etc/os-release ]; then
        # shellcheck source=/dev/null
        . /etc/os-release
        id="${ID:-}"
        pretty="${PRETTY_NAME:-$id}"
        case "$id" in
            debian|ubuntu) log "OS: $pretty" ;;
            *) warn "OS '$pretty' is not Debian/Ubuntu; the installer targets those (continuing)" ;;
        esac
    else
        warn "cannot read /etc/os-release; assuming a Debian/Ubuntu-like host"
    fi
}

check_tools() {
    command -v curl >/dev/null 2>&1 || die "curl is required"
}

check_docker() {
    HAVE_DOCKER=0
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        HAVE_DOCKER=1
        log "Docker: $(docker --version 2>/dev/null || echo present)"
        return 0
    fi

    if [ "$DRY_RUN" = 1 ]; then
        warn "docker/docker compose not available; docker checks and Caddy validation are skipped (dry-run)"
        return 0
    fi
    if [ "$NO_INSTALL_DOCKER" = 1 ]; then
        die "docker + 'docker compose' are required, and --no-install-docker is set"
    fi

    log "Installing Docker via https://get.docker.com ..."
    if ! curl -fsSL https://get.docker.com | sh; then
        die "Docker installation failed"
    fi
    systemctl enable --now docker >/dev/null 2>&1 || warn "could not enable/start docker via systemctl"
    command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 \
        || die "docker + 'docker compose' still unavailable after installation"
    HAVE_DOCKER=1
}

stack_running() {
    command -v docker >/dev/null 2>&1 || return 1
    # Project name is pinned to `hexaveil` in deploy/compose.install.yml.
    [ -n "$(docker ps -q --filter 'label=com.docker.compose.project=hexaveil' 2>/dev/null || true)" ]
}

check_ports() {
    local port line
    if ! command -v ss >/dev/null 2>&1; then
        warn "ss not found; skipping port checks"
        return 0
    fi

    if [ "$BEHIND_PROXY" = 1 ]; then
        port=3000
        line=$(ss -ltn 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print; found=1} END{exit(found?0:1)}' || true)
        if [ -n "$line" ]; then
            if stack_running; then
                warn "port $port is held by the existing HexaVeil stack (repeat run)"
            else
                warn "listener: $line"
                die "port $port is already in use; stop it or choose another proxy setup"
            fi
        fi
        return 0
    fi

    for port in 80 443; do
        line=$(ss -ltn 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" {print; found=1} END{exit(found?0:1)}' || true)
        if [ -n "$line" ]; then
            if stack_running; then
                warn "port $port is held by the existing HexaVeil stack (repeat run)"
            else
                warn "listener: $line"
                die "port $port is already in use; stop the listener or use --behind-proxy"
            fi
        fi
    done
}

check_disk() {
    local target avail_kb
    target="$INSTALL_ROOT"
    while [ -n "$target" ] && [ "$target" != "/" ] && [ ! -d "$target" ]; do
        target=$(dirname "$target")
    done
    [ -d "$target" ] || { warn "cannot determine install directory for disk check"; return 0; }
    avail_kb=$(df -Pk "$target" 2>/dev/null | awk 'NR==2 {print $4}')
    if [ -z "$avail_kb" ] || ! [ "$avail_kb" -ge 0 ] 2>/dev/null; then
        warn "could not read free disk space for $target"
        return 0
    fi
    if [ "$avail_kb" -lt 5242880 ]; then
        die "at least 5 GB free is required on $target (have $((avail_kb / 1024)) MB)"
    fi
    log "Free disk on $target: $((avail_kb / 1024)) MB"
}

check_ram() {
    local mem_kb
    [ -r /proc/meminfo ] || return 0
    mem_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
    if [ -n "$mem_kb" ] && [ "$mem_kb" -lt 1048576 ]; then
        warn "less than 1 GB RAM detected ($((mem_kb / 1024)) MB); the stack may be slow"
    fi
}

check_dns() {
    local external domain resolved
    command -v getent >/dev/null 2>&1 || { warn "getent not found; skipping DNS check"; return 0; }
    external=$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)
    if [ -z "$external" ]; then
        warn "could not determine the external IP; skipping DNS check"
        return 0
    fi
    for domain in "$SITE_DOMAIN" "$ADMIN_DOMAIN"; do
        resolved=$(getent ahostsv4 "$domain" 2>/dev/null | awk 'NR==1 {print $1}')
        if [ -z "$resolved" ]; then
            warn "DNS: $domain does not resolve yet (expected $external)"
        elif [ "$resolved" != "$external" ]; then
            warn "DNS: $domain -> $resolved (external IP is $external); behind NAT/proxy this may be fine"
        else
            log "DNS: $domain -> $resolved"
        fi
    done
}

validate_domain() {
    local value="$1" label="$2"
    [ -n "$value" ] || die "$label is empty"
    if ! [[ "$value" =~ ^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$ ]]; then
        die "invalid $label: '$value'"
    fi
}

validate_email() {
    local value="$1"
    [ -n "$value" ] || die "ACME email is empty"
    if ! [[ "$value" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]]; then
        die "invalid ACME email: '$value'"
    fi
}

# ── .env generation ──────────────────────────────────────────────────────────
set_env_kv() {
    local file="$1" key="$2" value="$3" force="${4:-0}"
    if grep -qE "^${key}=" "$file" 2>/dev/null; then
        if [ "$force" = 1 ]; then
            KEY="$key" VAL="$value" awk '
                BEGIN { ke = ENVIRON["KEY"]; va = ENVIRON["VAL"]; done = 0 }
                index($0, ke "=") == 1 { print ke "=" va; done = 1; next }
                { print }
                END { if (!done) print ke "=" va }
            ' "$file" > "${file}.awk" && mv "${file}.awk" "$file"
        fi
    else
        printf '%s=%s\n' "$key" "$value" >> "$file"
    fi
}

write_env() {
    local ts site_url admin_url cors tz force_derived
    local db_pass jwt_key app_key

    command -v openssl >/dev/null 2>&1 || {
        # Existing secrets are enough when openssl is unavailable.
        if [ -f "$ENV_FILE" ] \
            && [ -n "$(env_get "$ENV_FILE" DB_PASS)" ] \
            && [ -n "$(env_get "$ENV_FILE" JWT_SECRET)" ] \
            && [ -n "$(env_get "$ENV_FILE" APP_ENCRYPTION_KEY)" ]; then
            warn "openssl not found; reusing existing secrets from .env"
        else
            die "openssl is required to generate secrets"
        fi
    }

    umask 077

    if [ -f "$ENV_FILE" ]; then
        ts=$(date +%Y%m%d%H%M%S)
        cp -p "$ENV_FILE" "$ENV_FILE.bak.$ts"
        chmod 600 "$ENV_FILE.bak.$ts" 2>/dev/null || true
        log "Backed up .env -> .env.bak.$ts"
    fi

    ENV_TMP="$ENV_FILE.tmp.$$"
    : > "$ENV_TMP"
    if [ -f "$ENV_FILE" ]; then cat "$ENV_FILE" > "$ENV_TMP"; fi
    if [ -s "$ENV_TMP" ]; then
        if [ "$(tail -c 1 "$ENV_TMP" | od -An -t u1 | tr -d ' \n')" != "10" ]; then
            printf '\n' >> "$ENV_TMP"
        fi
    fi

    db_pass=$(env_get "$ENV_FILE" DB_PASS)
    jwt_key=$(env_get "$ENV_FILE" JWT_SECRET)
    app_key=$(env_get "$ENV_FILE" APP_ENCRYPTION_KEY)
    [ -n "$db_pass" ] || db_pass=$(gen_alnum)
    [ -n "$jwt_key" ] || jwt_key=$(gen_hex)
    [ -n "$app_key" ] || app_key=$(gen_hex)

    tz=$(cat /etc/timezone 2>/dev/null || true)
    [ -n "$tz" ] || tz="UTC"

    site_url="https://${SITE_DOMAIN}"
    admin_url="https://${ADMIN_DOMAIN}"
    cors="${admin_url},${site_url}"

    force_derived=0
    if [ "$RECONFIGURE_DOMAINS" = 1 ] || [ "$DRY_RUN" = 1 ]; then force_derived=1; fi

    set_env_kv "$ENV_TMP" DB_DRIVER pgsql 0
    set_env_kv "$ENV_TMP" DB_HOST db 0
    set_env_kv "$ENV_TMP" DB_PORT 5432 0
    set_env_kv "$ENV_TMP" DB_NAME cms 0
    set_env_kv "$ENV_TMP" DB_USER cms 0
    set_env_kv "$ENV_TMP" DB_PASS "$db_pass" 0
    set_env_kv "$ENV_TMP" JWT_SECRET "$jwt_key" 0
    set_env_kv "$ENV_TMP" APP_ENCRYPTION_KEY "$app_key" 0
    set_env_kv "$ENV_TMP" APP_DEBUG false 0
    set_env_kv "$ENV_TMP" SITE_NAME "$SITE_NAME" "$SITE_NAME_EXPLICIT"
    set_env_kv "$ENV_TMP" SITE_URL "$site_url" "$force_derived"
    set_env_kv "$ENV_TMP" CMS_PUBLIC_URL "$admin_url" "$force_derived"
    set_env_kv "$ENV_TMP" CORS_ORIGINS "$cors" "$force_derived"
    set_env_kv "$ENV_TMP" ADMIN_EMAIL "$ACME_EMAIL" "$force_derived"
    set_env_kv "$ENV_TMP" ADMIN_LOGIN "$ADMIN_LOGIN" "$ADMIN_LOGIN_EXPLICIT"
    set_env_kv "$ENV_TMP" SITE_DOMAIN "$SITE_DOMAIN" "$force_derived"
    set_env_kv "$ENV_TMP" ADMIN_DOMAIN "$ADMIN_DOMAIN" "$force_derived"
    set_env_kv "$ENV_TMP" ACME_EMAIL "$ACME_EMAIL" "$force_derived"
    set_env_kv "$ENV_TMP" TZ "$tz" 0
    set_env_kv "$ENV_TMP" MAX_UPLOAD_SIZE 67108864 0
    set_env_kv "$ENV_TMP" LOG_DIR /app/logs 0
    set_env_kv "$ENV_TMP" CMS_HTTP_PORT 3000 0
    set_env_kv "$ENV_TMP" CMS_BIND_IP 127.0.0.1 0

    mv -f "$ENV_TMP" "$ENV_FILE"
    ENV_TMP=""
    chmod 600 "$ENV_FILE"
    log "Wrote $ENV_FILE (mode 0600)"
}

# ── compose wrapper ──────────────────────────────────────────────────────────
# The compose file lives in deploy/, so interpolation .env must be passed
# explicitly: Compose would otherwise look for deploy/.env.
# stdin is /dev/null on purpose: in `curl | bash` mode stdin carries this
# script, and child processes (docker compose exec, psql, ...) would drain it
# and silently truncate the install at the first exec. Prompts use /dev/tty.
compose() {
    if [ "$BEHIND_PROXY" = 1 ]; then
        docker compose --env-file "$ENV_FILE" \
            -f "$REPO_ROOT/deploy/compose.install.yml" \
            -f "$REPO_ROOT/deploy/compose.behind-proxy.yml" "$@" </dev/null
    else
        docker compose --env-file "$ENV_FILE" \
            -f "$REPO_ROOT/deploy/compose.install.yml" "$@" </dev/null
    fi
}

ensure_behind_proxy_override() {
    local file="$REPO_ROOT/deploy/compose.behind-proxy.yml"
    if [ -f "$file" ]; then return 0; fi
    {
        printf '%s\n' "$MANAGED_MARKER"
        cat <<'YAML'
services:
  web:
    ports:
      - "127.0.0.1:${CMS_HTTP_PORT:-3000}:80"
YAML
    } > "$file"
    chmod 644 "$file"
    log "Created $file"
}

# ── stack lifecycle ──────────────────────────────────────────────────────────
wait_pg() {
    local i=0
    log "Waiting for PostgreSQL (up to 60s) ..."
    until compose exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
        i=$((i + 1))
        if [ "$i" -ge 60 ]; then
            compose logs --tail=100 db || true
            die "PostgreSQL did not become ready within 60s"
        fi
        sleep 1
    done
    log "PostgreSQL is ready"
}

backup_before_migrate() {
    local exists ts out
    exists=$(compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc \
        "SELECT to_regclass('public.users') IS NOT NULL" 2>/dev/null | tr -d '[:space:]' || true)
    if [ "$exists" != "t" ] && [ "$ADOPT_EXISTING" != 1 ]; then
        log "No public.users yet — nothing to back up before migrate"
        return 0
    fi

    mkdir -p "$REPO_ROOT/deploy/backups"
    chmod 700 "$REPO_ROOT/deploy/backups" 2>/dev/null || true
    ts=$(date +%Y%m%d-%H%M%S)
    out="$REPO_ROOT/deploy/backups/pre-migrate-$ts.sql"
    compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" > "$out"
    chmod 600 "$out" 2>/dev/null || true
    log "Pre-migrate database backup: $out"
}

run_migrations() {
    log "Running database migrations (one-shot migrate service) ..."
    if ! compose up --build --abort-on-container-exit --exit-code-from migrate migrate; then
        printf '\n──── migrate logs ────\n' >&2
        compose logs --tail=200 migrate || true
        die "migrations failed; see the logs above"
    fi
    log "Migrations completed"
}

wait_api() {
    local i=0
    log "Waiting for the API health endpoint (up to 90s) ..."
    until compose exec -T api python -c \
        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=5)" \
        >/dev/null 2>&1; do
        i=$((i + 1))
        if [ "$i" -ge 90 ]; then
            compose logs --tail=100 api || true
            die "API did not become healthy within 90s"
        fi
        sleep 1
    done
    log "API is healthy"
}

remove_admin_password_from_env() {
    if grep -q '^ADMIN_PASSWORD=' "$ENV_FILE" 2>/dev/null; then
        sed -i '/^ADMIN_PASSWORD=/d' "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log "Removed ADMIN_PASSWORD from .env"
    fi
}

# Admin password: the decision needs the database (was the admin user created?),
# so it runs after migrations instead of before the stack starts. This keeps a
# re-run after a failed install from skipping the password just because .env
# already exists.
admin_user_exists() {
    local out=""
    out=$(compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" \
        -v login="$ADMIN_LOGIN" -tAc \
        "SELECT 1 FROM users WHERE login = :'login' LIMIT 1" 2>/dev/null \
        | tr -d '[:space:]' || true)
    [ "$out" = "1" ]
}

ensure_admin_password() {
    local needs_password=0
    if [ "$RESET_ADMIN_PASSWORD" = 1 ]; then
        needs_password=1
    elif ! admin_user_exists; then
        needs_password=1
    fi

    if [ "$needs_password" != 1 ]; then
        if [ -n "${ADMIN_PASSWORD-}" ]; then
            warn "existing admin '$ADMIN_LOGIN': password unchanged (use --reset-admin-password to rotate)"
        fi
        return 0
    fi

    if [ -n "${ADMIN_PASSWORD-}" ]; then return 0; fi

    if [ "$NON_INTERACTIVE" = 1 ]; then
        ADMIN_PASSWORD=$(gen_password)
        PASSWORD_GENERATED=1
        return 0
    fi

    ask_secret "Пароль администратора $ADMIN_LOGIN (Enter — сгенерировать): "
    ADMIN_PASSWORD="$ANSWER"
    if [ -z "$ADMIN_PASSWORD" ]; then
        ADMIN_PASSWORD=$(gen_password)
        PASSWORD_GENERATED=1
    fi
}

bootstrap_admin() {
    local code=0 out="" args=()
    args=(-T -e "ADMIN_LOGIN=$ADMIN_LOGIN")
    if [ -n "${ADMIN_EMAIL-}" ]; then args+=(-e "ADMIN_EMAIL=$ADMIN_EMAIL"); fi
    if [ -n "${ADMIN_PASSWORD-}" ]; then args+=(-e "ADMIN_PASSWORD=$ADMIN_PASSWORD"); fi
    if [ "$RESET_ADMIN_PASSWORD" = 1 ] && [ -n "${ADMIN_PASSWORD-}" ]; then
        args+=(-e "FORCE_RESET=1")
    fi

    out=$(compose exec "${args[@]}" app php /var/www/html/deploy/bootstrap_admin.php 2>&1) || code=$?
    printf '%s\n' "$out"

    case "$out" in
        *"Created admin"*|*"Set password"*|*"Reset password"*) PASSWORD_APPLIED=1 ;;
    esac

    if [ "$code" -eq 2 ]; then
        die "admin bootstrap requires a password. Re-run with --admin-password '<password>' (add --reset-admin-password to rotate an existing admin)."
    elif [ "$code" -ne 0 ]; then
        die "admin bootstrap failed (exit $code)"
    fi

    if [ "$PASSWORD_APPLIED" = 1 ] && [ -n "${ADMIN_PASSWORD-}" ]; then
        PRINT_PASSWORD=1
    fi
    if [ "$PASSWORD_APPLIED" = 1 ] && [ "$PASSWORD_GENERATED" = 1 ]; then
        CREDENTIALS_FILE="$INSTALL_ROOT/.install-credentials"
        ( umask 077; printf 'login=%s\npassword=%s\n' "$ADMIN_LOGIN" "$ADMIN_PASSWORD" > "$CREDENTIALS_FILE" )
        chmod 600 "$CREDENTIALS_FILE"
    fi

    remove_admin_password_from_env
}

wait_tls() {
    local i=0
    log "Waiting for TLS on https://$ADMIN_DOMAIN (up to 120s) ..."
    until curl -sSf --resolve "$ADMIN_DOMAIN:443:127.0.0.1" \
        "https://$ADMIN_DOMAIN/api/health" >/dev/null 2>&1; do
        i=$((i + 1))
        if [ "$i" -ge 40 ]; then
            warn "TLS is not ready after 120s. Check:"
            warn "  * DNS A records for $SITE_DOMAIN and $ADMIN_DOMAIN point to this server"
            warn "  * inbound TCP port 80 is reachable (ACME HTTP challenge)"
            warn "  * caddy logs: cd $INSTALL_ROOT && sudo docker compose --env-file .env -f deploy/compose.install.yml logs caddy"
            HEALTH_LINE="not ready (see warning above)"
            return 0
        fi
        sleep 3
    done
    HEALTH_LINE="https://$ADMIN_DOMAIN/api/health -> 200"
    log "TLS is ready"
}

# ── host nginx fallback (--behind-proxy) ─────────────────────────────────────
render_nginx_site() {
    local template="$1" dest="$2" token="$3" domain="$4"
    if [ -f "$dest" ] && ! grep -qF "$MANAGED_MARKER" "$dest"; then
        warn "not overwriting $dest (no '$MANAGED_MARKER' marker)"
        return 0
    fi
    mkdir -p "$(dirname "$dest")"
    {
        printf '%s\n' "$MANAGED_MARKER"
        sed "s|$token|$domain|g" "$template"
    } > "${dest}.tmp"
    mv "${dest}.tmp" "$dest"
    chmod 644 "$dest"
}

# Render the two-domain bootstrap template (both __SITE_DOMAIN__ and
# __ADMIN_DOMAIN__ substituted in one pass, same marker guard as above).
render_nginx_bootstrap() {
    local template="$1" dest="$2"
    if [ -f "$dest" ] && ! grep -qF "$MANAGED_MARKER" "$dest"; then
        warn "not overwriting $dest (no '$MANAGED_MARKER' marker)"
        return 0
    fi
    mkdir -p "$(dirname "$dest")"
    {
        printf '%s\n' "$MANAGED_MARKER"
        sed -e "s|__SITE_DOMAIN__|$SITE_DOMAIN|g" \
            -e "s|__ADMIN_DOMAIN__|$ADMIN_DOMAIN|g" "$template"
    } > "${dest}.tmp"
    mv "${dest}.tmp" "$dest"
    chmod 644 "$dest"
}

setup_host_nginx() {
    local avail bootstrap_conf bootstrap_link site_cert admin_cert certbot_manual
    if ! command -v nginx >/dev/null 2>&1; then
        warn "nginx not found; skipped host-nginx setup (install nginx and re-run with --behind-proxy)"
        return 0
    fi

    avail="/etc/nginx/sites-available"
    bootstrap_conf="$avail/hexaveil-bootstrap.conf"
    bootstrap_link="/etc/nginx/sites-enabled/hexaveil-bootstrap.conf"
    site_cert="/etc/letsencrypt/live/$SITE_DOMAIN/fullchain.pem"
    admin_cert="/etc/letsencrypt/live/$ADMIN_DOMAIN/fullchain.pem"
    certbot_manual="certbot certonly --webroot -w /var/www/certbot -d $SITE_DOMAIN -d $ADMIN_DOMAIN --email $ACME_EMAIL --agree-tos -n"

    mkdir -p "$avail" /etc/nginx/sites-enabled /var/www/certbot
    if [ ! -f /etc/nginx/conf.d/00-hexaveil-upgrade-map.conf ]; then
        cp "$REPO_ROOT/deploy/nginx-host/00-upgrade-map.conf" \
            /etc/nginx/conf.d/00-hexaveil-upgrade-map.conf 2>/dev/null || \
            warn "could not install the WebSocket upgrade map"
    fi

    # ── Phase 1: HTTP-only bootstrap config. The 443 blocks cannot be rendered
    # before certificates exist (nginx -t would fail on missing .pem files), so
    # serve the ACME webroot on port 80 first.
    render_nginx_bootstrap \
        "$REPO_ROOT/deploy/nginx-host/bootstrap-http.conf.template" "$bootstrap_conf"
    ln -sf "$bootstrap_conf" "$bootstrap_link"

    if nginx -t 2>&1; then
        systemctl reload nginx 2>/dev/null || warn "could not reload nginx"
    else
        warn "nginx -t failed with the HTTP bootstrap config; fix the errors above and re-run --behind-proxy"
        warn "  (certbot was NOT attempted)"
        return 0
    fi

    # ── Phase 2: obtain certificates only when missing. One certonly call
    # covers both domains via the shared webroot.
    if [ -f "$site_cert" ] && [ -f "$admin_cert" ]; then
        log "TLS certificates already present for $SITE_DOMAIN and $ADMIN_DOMAIN"
    elif command -v certbot >/dev/null 2>&1; then
        log "Requesting certificates with certbot (webroot) ..."
        if ! certbot certonly --webroot -w /var/www/certbot \
            -d "$SITE_DOMAIN" -d "$ADMIN_DOMAIN" \
            --email "$ACME_EMAIL" --agree-tos -n; then
            warn "certbot failed; the temporary HTTP config stays active. After fixing DNS/ports run:"
            warn "  $certbot_manual"
            warn "  sudo bash deploy/install.sh --behind-proxy"
        fi
    else
        warn "certbot is not installed; the temporary HTTP config stays active (TLS is NOT ready)."
        warn "Install certbot, then run:"
        warn "  $certbot_manual"
        warn "  sudo bash deploy/install.sh --behind-proxy"
    fi

    # ── Phase 3: switch to the full TLS configs only when BOTH cert files exist.
    if [ -f "$site_cert" ] && [ -f "$admin_cert" ]; then
        render_nginx_site "$REPO_ROOT/deploy/nginx-host/site.conf.template" \
            "$avail/hexaveil-site.conf" "__SITE_DOMAIN__" "$SITE_DOMAIN"
        render_nginx_site "$REPO_ROOT/deploy/nginx-host/admin.conf.template" \
            "$avail/hexaveil-admin.conf" "__ADMIN_DOMAIN__" "$ADMIN_DOMAIN"
        ln -sf "$avail/hexaveil-site.conf" /etc/nginx/sites-enabled/hexaveil-site.conf
        ln -sf "$avail/hexaveil-admin.conf" /etc/nginx/sites-enabled/hexaveil-admin.conf
        rm -f "$bootstrap_link"

        if nginx -t 2>&1; then
            # Drop the managed bootstrap file only after a successful test.
            if [ -f "$bootstrap_conf" ] && grep -qF "$MANAGED_MARKER" "$bootstrap_conf"; then
                rm -f "$bootstrap_conf"
            fi
            systemctl reload nginx 2>/dev/null || warn "could not reload nginx"
        else
            warn "nginx -t failed with the TLS configs (both certificates may not be valid yet)"
            warn "re-enabling the temporary HTTP bootstrap config"
            rm -f /etc/nginx/sites-enabled/hexaveil-site.conf \
                  /etc/nginx/sites-enabled/hexaveil-admin.conf
            ln -sf "$bootstrap_conf" "$bootstrap_link"
            if nginx -t 2>&1; then
                systemctl reload nginx 2>/dev/null || warn "could not reload nginx"
            else
                warn "nginx -t still fails; nginx was NOT reloaded"
            fi
        fi
    else
        warn "skipping the TLS config: fullchain.pem is missing for $SITE_DOMAIN and/or $ADMIN_DOMAIN"
    fi

    if curl -fsS --max-time 5 http://127.0.0.1:3000/api/health >/dev/null 2>&1; then
        HEALTH_LINE="http://127.0.0.1:3000/api/health -> 200 (host nginx in front)"
    else
        HEALTH_LINE="unknown (check http://127.0.0.1:3000/api/health)"
    fi
}

# ── summaries ────────────────────────────────────────────────────────────────
summary() {
    printf '\n'
    printf '==============================================================\n'
    printf ' HexaVeil CMS установлен\n'
    printf '==============================================================\n'
    printf ' Публичный сайт : https://%s\n' "$SITE_DOMAIN"
    printf ' Админка        : https://%s/admin/\n' "$ADMIN_DOMAIN"
    printf ' Health         : %s\n' "$HEALTH_LINE"
    printf ' Логин          : %s\n' "$ADMIN_LOGIN"
    if [ "$PRINT_PASSWORD" = 1 ]; then
        printf ' Пароль         : %s\n' "$ADMIN_PASSWORD"
        if [ -n "$CREDENTIALS_FILE" ]; then
            printf '                  сохранён в %s (0600)\n' "$CREDENTIALS_FILE"
            printf '                  ⚠ сохраните и удалите файл: sudo rm %s\n' "$CREDENTIALS_FILE"
        fi
    else
        printf ' Пароль         : не изменялся (используйте --reset-admin-password для смены)\n'
    fi
    printf ' Каталог        : %s\n' "$INSTALL_ROOT"
    printf ' Управление     : cd %s && sudo docker compose --env-file .env -f deploy/compose.install.yml ps\n' "$INSTALL_ROOT"
    printf ' Логи           : cd %s && sudo docker compose --env-file .env -f deploy/compose.install.yml logs -f\n' "$INSTALL_ROOT"
    printf ' Повторный запуск безопасен: секреты, тома и БД не меняются.\n'
    printf '==============================================================\n'
}

summary_dry_run() {
    local mode="caddy (80/443)"
    if [ "$BEHIND_PROXY" = 1 ]; then mode="behind-proxy (127.0.0.1:3000)"; fi
    printf '\n'
    printf '==============================================================\n'
    printf ' HexaVeil CMS — dry run OK\n'
    printf '==============================================================\n'
    printf ' Публичный сайт : https://%s\n' "$SITE_DOMAIN"
    printf ' Админка        : https://%s/admin/\n' "$ADMIN_DOMAIN"
    printf ' .env           : %s (0600)\n' "$ENV_FILE"
    printf ' Caddyfile      : validated\n'
    printf ' Контейнеры     : не запускались\n'
    printf ' БД и админ     : не изменялись\n'
    printf ' Каталог        : %s\n' "$INSTALL_ROOT"
    printf ' Режим          : %s\n' "$mode"
    printf '==============================================================\n'
}

# ── main ─────────────────────────────────────────────────────────────────────
detect_tty
check_root
check_os
check_tools

resolve_repo

ENV_FILE="$REPO_ROOT/.env"
INSTALL_ROOT="$REPO_ROOT"
if [ -f "$ENV_FILE" ]; then ENV_EXISTED=1; fi

# Reuse values from an existing .env on a repeat run.
if [ "$ENV_EXISTED" = 1 ]; then
    if [ -z "$SITE_DOMAIN" ]; then SITE_DOMAIN=$(env_get "$ENV_FILE" SITE_DOMAIN); fi
    if [ -z "$ADMIN_DOMAIN" ]; then ADMIN_DOMAIN=$(env_get "$ENV_FILE" ADMIN_DOMAIN); fi
    if [ -z "$ACME_EMAIL" ]; then ACME_EMAIL=$(env_get "$ENV_FILE" ACME_EMAIL); fi
    if [ -z "$ADMIN_EMAIL" ]; then ADMIN_EMAIL=$(env_get "$ENV_FILE" ADMIN_EMAIL); fi
    if [ -z "$ADMIN_LOGIN" ]; then ADMIN_LOGIN=$(env_get "$ENV_FILE" ADMIN_LOGIN); fi
    if [ -z "$SITE_NAME" ]; then SITE_NAME=$(env_get "$ENV_FILE" SITE_NAME); fi
fi

if [ -z "$ADMIN_LOGIN" ]; then ADMIN_LOGIN="admin"; fi
if [ -z "$SITE_NAME" ]; then SITE_NAME="HexaVeil"; fi

if [ "$NON_INTERACTIVE" = 1 ]; then
    [ -n "$SITE_DOMAIN" ] || die "--site-domain (or SITE_DOMAIN) is required with --non-interactive"
    [ -n "$ADMIN_DOMAIN" ] || die "--admin-domain (or ADMIN_DOMAIN) is required with --non-interactive"
    [ -n "$ACME_EMAIL" ] || die "--acme-email (or ACME_EMAIL) is required with --non-interactive"
else
    if [ -z "$SITE_DOMAIN" ]; then ask_text "Публичный домен (SITE_DOMAIN): "; SITE_DOMAIN="$ANSWER"; fi
    if [ -z "$ADMIN_DOMAIN" ]; then ask_text "Домен админки (ADMIN_DOMAIN): "; ADMIN_DOMAIN="$ANSWER"; fi
    if [ -z "$ACME_EMAIL" ]; then ask_text "Email для ACME (ACME_EMAIL): "; ACME_EMAIL="$ANSWER"; fi
fi

validate_domain "$SITE_DOMAIN" "SITE_DOMAIN"
validate_domain "$ADMIN_DOMAIN" "ADMIN_DOMAIN"
validate_email "$ACME_EMAIL"
[ "$SITE_DOMAIN" != "$ADMIN_DOMAIN" ] || die "SITE_DOMAIN and ADMIN_DOMAIN must differ"
if [ -z "$ADMIN_EMAIL" ]; then ADMIN_EMAIL="$ACME_EMAIL"; fi

# Repeat run: domains may only change with --reconfigure-domains.
if [ "$ENV_EXISTED" = 1 ] && [ "$RECONFIGURE_DOMAINS" != 1 ]; then
    old_site=$(env_get "$ENV_FILE" SITE_DOMAIN)
    old_admin=$(env_get "$ENV_FILE" ADMIN_DOMAIN)
    if [ -n "$old_site" ] && [ "$old_site" != "$SITE_DOMAIN" ]; then
        if [ "$DRY_RUN" = 1 ]; then
            warn "dry-run: SITE_DOMAIN differs from .env ('$old_site' -> '$SITE_DOMAIN')"
        else
            die "SITE_DOMAIN differs from the existing .env ('$old_site'); use --reconfigure-domains"
        fi
    fi
    if [ -n "$old_admin" ] && [ "$old_admin" != "$ADMIN_DOMAIN" ]; then
        if [ "$DRY_RUN" = 1 ]; then
            warn "dry-run: ADMIN_DOMAIN differs from .env ('$old_admin' -> '$ADMIN_DOMAIN')"
        else
            die "ADMIN_DOMAIN differs from the existing .env ('$old_admin'); use --reconfigure-domains"
        fi
    fi
fi

check_docker
check_ports
check_disk
check_ram
check_dns

if [ "$BEHIND_PROXY" = 1 ]; then
    log "Mode: behind-proxy (web published on 127.0.0.1:3000)"
else
    log "Mode: caddy (ports 80/443)"
fi
if [ "$ADOPT_EXISTING" = 1 ]; then log "Mode: adopt-existing (secrets/data preserved)"; fi
if [ "$DRY_RUN" = 1 ]; then log "Mode: dry-run (no containers will start)"; fi

write_env

# Admin password is decided after migrations (see ensure_admin_password), once
# the users table exists.

if [ "$DRY_RUN" = 1 ]; then
    log "Validating Caddyfile ..."
    if [ "$HAVE_DOCKER" = 1 ]; then
        # Git Bash rewrites Unix-looking arguments for native docker.exe; keep
        # the in-container Caddyfile path untouched.
        if MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker run --rm \
            -e "SITE_DOMAIN=$SITE_DOMAIN" \
            -e "ADMIN_DOMAIN=$ADMIN_DOMAIN" \
            -e "ACME_EMAIL=$ACME_EMAIL" \
            -v "$(host_path "$REPO_ROOT/deploy/Caddyfile"):/etc/caddy/Caddyfile:ro" \
            caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile </dev/null; then
            log "Caddyfile validation: OK"
        else
            die "Caddyfile validation failed"
        fi
    else
        warn "docker unavailable; skipped Caddyfile validation"
    fi
    summary_dry_run
    exit 0
fi

if [ "$BEHIND_PROXY" = 1 ]; then
    ensure_behind_proxy_override
fi

log "Starting the database ..."
DB_USER=$(env_get "$ENV_FILE" DB_USER); DB_USER=${DB_USER:-cms}
DB_NAME=$(env_get "$ENV_FILE" DB_NAME); DB_NAME=${DB_NAME:-cms}
compose up -d db
wait_pg

backup_before_migrate
run_migrations
ensure_admin_password

log "Starting application services ..."
if [ "$BEHIND_PROXY" = 1 ]; then
    compose up -d --build app api web
else
    compose up -d --build app api web caddy
fi

wait_api
bootstrap_admin

if [ "$BEHIND_PROXY" = 1 ]; then
    setup_host_nginx
else
    wait_tls
fi

summary
