# HexaVeil CMS — one-command deploy

Installer: `deploy/install.sh`. It generates `.env`, starts Postgres, runs
migrations (ledger-tracked), boots the stack, and creates the admin user.
The compose project is pinned to `hexaveil`, so volumes are always
`hexaveil_pgdata`, `hexaveil_uploads_data`, `hexaveil_backup_data`,
`hexaveil_caddy_data`, `hexaveil_caddy_config` regardless of the checkout
directory. Full reference: [`../DEPLOY.md`](../DEPLOY.md).

## Quickstart (2 commands)

```bash
git clone https://github.com/imcrazymonk-pixel/cms.git /opt/hexaveil-cms
cd /opt/hexaveil-cms && sudo bash deploy/install.sh
```

It asks for `SITE_DOMAIN`, `ADMIN_DOMAIN`, `ACME_EMAIL`, `ADMIN_LOGIN`
(default `admin`), and the admin password (empty = generate). TLS is handled
by Caddy; the password is printed once and written to `.install-credentials`.

## Non-interactive

```bash
sudo bash deploy/install.sh \
  --site-domain example.com --admin-domain admin.example.com \
  --acme-email ops@example.com --non-interactive
```

## curl | bash (public repo)

```bash
curl -fsSL https://raw.githubusercontent.com/imcrazymonk-pixel/cms/main/deploy/install.sh \
  | sudo bash -s -- --site-domain example.com --admin-domain admin.example.com \
                     --acme-email ops@example.com
```

## Host nginx / selfsteal (ports 80/443 already taken)

```bash
sudo bash deploy/install.sh --behind-proxy ...
```

Publishes `127.0.0.1:${CMS_HTTP_PORT:-3000}`, writes
`/etc/nginx/sites-available/hexaveil-*.conf`, and bootstraps certificates in
two phases: an HTTP-only ACME webroot config on port 80, then
`certbot certonly --webroot`, then the TLS blocks (only when both certs
exist). certbot is never installed silently; re-running the installer is safe
and resumes the switch.

## Re-run / adopt existing

- Re-running is safe: secrets, `hexaveil_*` volumes, the migration ledger, and
  the admin password are preserved. Change domains only with
  `--reconfigure-domains`; rotate the password with `--reset-admin-password`.
- Migrating an existing install: add `--adopt-existing` (a `pg_dump` is taken
  to `deploy/backups/pre-migrate-<ts>.sql`; `01-schema.sql` is skipped when
  `users` exists; no `down -v`).
- Save and delete `../.install-credentials` (0600) after install; keep
  `backups/` private.
- The legacy host-nginx stack is still `docker-compose.prod.yml` + `deploy.sh`
  (`hexacms_*` containers) — do not mix it with the `hexaveil` project.

## Troubleshooting

- **Ports 80/443 busy** — stop the listener or use `--behind-proxy`.
- **DNS** — A records for both domains must point at the server; ACME needs
  inbound port 80. DNS mismatches are warnings, not aborts.
- **TLS not ready** — the installer waits 120s, then warns; check Caddy logs.
- **Forgot the password** — `sudo bash deploy/install.sh --reset-admin-password`
  on the same checkout.
- **`migrations failed`** — `docker compose --env-file .env -f deploy/compose.install.yml logs migrate`;
  fix the SQL/data, then `... run --rm migrate`.
- **`checksum mismatch`** — a migration file changed after it was applied; this
  is a warning, do not delete its ledger row.
- **`--dry-run`** — checks, writes `.env`, validates the Caddyfile; starts nothing.
