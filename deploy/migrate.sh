#!/bin/sh
# ─────────────────────────────────────────────────────────────
# HexaVeil CMS — database bootstrap + file migrations with a ledger.
#
# Runs inside postgres:16-alpine with the repository `db/` tree mounted
# read-only at /db (and this script at /migrate.sh). Connection settings
# come from the same DB_* env vars the app uses; PGHOST/PGPORT/PGUSER/
# PGDATABASE are derived so plain `psql` works too.
#
# Behaviour:
#   1. wait for pg_isready (up to 60s);
#   2. create the schema_migrations ledger;
#   3. bootstrap db/postgres/init/01-schema.sql only when public.users is
#      absent (adopt-existing installs already have it);
#   4. apply, in order, db/postgres/migrations/*.sql then db/migrations/*.sql,
#      skipping anything recorded in the ledger;
#   5. warn (not fail) on checksum drift, fail on SQL errors.
#
# Idempotent: a second run applies nothing and reports skipped counts.
# ─────────────────────────────────────────────────────────────
set -eu

DB_DIR="${DB_DIR:-/db}"

DB_PASS="${DB_PASS:-cms}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-cms}"
DB_NAME="${DB_NAME:-cms}"

export PGPASSWORD="$DB_PASS"
export PGHOST="$DB_HOST"
export PGPORT="$DB_PORT"
export PGUSER="$DB_USER"
export PGDATABASE="$DB_NAME"

log() {
    printf '%s\n' "$*"
}

# Quiet, machine-readable single-value query (no headers, no padding).
psql_q() {
    psql -X -q -t -A -v ON_ERROR_STOP=1 "$@"
}

sum_of() {
    sha256sum "$1" | cut -d' ' -f1
}

log "==> waiting for PostgreSQL at ${PGHOST}:${PGPORT} (up to 60s)"
waited=0
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" >/dev/null 2>&1; do
    waited=$((waited + 1))
    if [ "$waited" -ge 60 ]; then
        log "ERROR: PostgreSQL is not ready after 60s (${PGHOST}:${PGPORT})." >&2
        exit 1
    fi
    sleep 1
done

log "==> ensuring schema_migrations ledger"
psql_q -c "CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text PRIMARY KEY,
    checksum   text,
    applied_at timestamptz NOT NULL DEFAULT now()
);"

ledger_has() {
    [ "$(psql_q -c "SELECT 1 FROM schema_migrations WHERE version = '$1' LIMIT 1" || true)" = "1" ]
}

ledger_checksum() {
    psql_q -c "SELECT COALESCE(checksum, '') FROM schema_migrations WHERE version = '$1'" || true
}

applied=0
skipped=0

# ── Bootstrap (fresh database only) ────────────────────────────────────────
init_file="${DB_DIR}/postgres/init/01-schema.sql"
users_present="$(psql_q -c "SELECT to_regclass('public.users') IS NOT NULL" || true)"

if [ "$users_present" != "t" ]; then
    if [ ! -f "$init_file" ]; then
        log "ERROR: bootstrap file not found: ${init_file}" >&2
        exit 1
    fi
    log "==> bootstrapping schema from init/01-schema.sql"
    if ! psql -X -q -v ON_ERROR_STOP=1 -f "$init_file"; then
        log "ERROR: bootstrap failed: init/01-schema.sql" >&2
        exit 1
    fi
    init_sum="$(sum_of "$init_file")"
    psql_q -c "INSERT INTO schema_migrations (version, checksum)
               VALUES ('init/01-schema.sql', '${init_sum}')
               ON CONFLICT (version) DO NOTHING;"
    applied=$((applied + 1))
else
    log "==> public.users already present — skipping init/01-schema.sql"
fi

# ── File migrations ────────────────────────────────────────────────────────
apply_file() {
    file="$1"
    version="$2"
    checksum="$(sum_of "$file")"

    if ledger_has "$version"; then
        previous="$(ledger_checksum "$version")"
        if [ -n "$previous" ] && [ "$previous" != "$checksum" ]; then
            log "WARNING: checksum mismatch for ${version} (ledger=${previous}, file=${checksum}); continuing"
        fi
        log "    skip  ${version}"
        skipped=$((skipped + 1))
        return 0
    fi

    log "    apply ${version}"
    if ! psql -X -q -v ON_ERROR_STOP=1 -f "$file"; then
        log "ERROR: migration failed: ${version}" >&2
        exit 1
    fi
    psql_q -c "INSERT INTO schema_migrations (version, checksum)
               VALUES ('${version}', '${checksum}')
               ON CONFLICT (version) DO NOTHING;"
    applied=$((applied + 1))
}

for dir in "${DB_DIR}/postgres/migrations" "${DB_DIR}/migrations"; do
    [ -d "$dir" ] || continue
    rel="${dir#"${DB_DIR}"/}"
    for file in "$dir"/*.sql; do
        [ -f "$file" ] || continue
        apply_file "$file" "${rel}/$(basename "$file")"
    done
done

log ""
log "==> migrations summary: applied=${applied} skipped=${skipped}"
