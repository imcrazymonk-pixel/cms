# HexaVeil Backup Agent

Небольшой сервис на каждом сервере: собирает дампы БД и файлов по рецептам,
шифрует, складывает в spool и отправляет в CMS. Работает по локальному
расписанию даже когда CMS недоступна.

## Установка

Из CMS: **Инфраструктура → Бэкапы → Хосты → Команда / По SSH**. CMS покажет
готовую команду:

```bash
curl -sSL https://hexaveil.xyz/api/backup-agent/v1/install.sh | bash -s -- \
  --url https://hexaveil.xyz --host-id <uuid> --token <token>
```

Требования:

1. `--url` — **публичный** адрес CMS, доступный с этого сервера. `127.0.0.1`
   и `localhost` запрещены (это адрес самой ноды, а не CMS).
2. У сервера есть **исходящий HTTPS** до CMS и до registry/архива образа.
3. Root или `sudo` без пароля.

Альтернатива — автоустановка по SSH из UI: если у хоста задан приватный ключ,
CMS подключится сама (`via=ssh`). Ключ хранится зашифрованным.

Флаги: `--url`, `--host-id`, `--token`, `--role server|node`, `--image <ref>`,
`--image-tarball <url|path>`.

### Если образа нет в registry

Образ `ghcr.io/hexaveil/backup-agent:latest` нужно опубликовать либо доставить
архивом:

```bash
# на машине, где образ собран
docker save -o agent.tar hexaveil/backup-agent:dev
scp -P 356 agent.tar root@<node>:/tmp/

# на ноде
curl -sSL https://hexaveil.xyz/api/backup-agent/v1/install.sh | bash -s -- \
  --url https://hexaveil.xyz --host-id <uuid> --token <token> \
  --image hexaveil/backup-agent:dev --image-tarball /tmp/agent.tar
```

Ещё вариант: положить архив на CMS (`backup-agent/agent-image.tar` или путь в
`AGENT_IMAGE_TARBALL_PATH`) — установщик сам скачает его с
`/api/backup-agent/v1/image`.


## Что монтируется

| Хост | В контейнер | Режим |
|------|-------------|-------|
| `/var/run/docker.sock` | тот же | rw (нужен для `docker exec`/`tar`) |
| `/opt/remnawave` | `/host/opt/remnawave` | ro |
| `/opt/remnanode` | `/host/opt/remnanode` | ro |
| `/srv/cabinet` | `/host/srv/cabinet` | ro |
| volume `agent_spool` | `/var/lib/hexaveil-agent` | rw |

Отсутствующие каталоги не создаются на хосте (`create_host_path: false`).

## Переменные окружения

| Переменная | По умолчанию | Смысл |
|-----------|--------------|-------|
| `AGENT_URL` | — | база CMS |
| `AGENT_HOST_ID` | — | UUID хоста |
| `AGENT_TOKEN` | — | токен агента |
| `AGENT_SPOOL_DIR` | `/var/lib/hexaveil-agent` | кэш и очередь |
| `AGENT_HOST_PREFIX` | `/host` | где смонтирована ФС хоста |
| `AGENT_AGE_RECIPIENT` | пусто | публичный ключ age для шифрования |
| `AGENT_AGE_IDENTITY` | пусто | приватный ключ (только для restore) |
| `AGENT_LOG_LEVEL` | `info` | логи |

## Обновление

```bash
cd /opt/hexaveil-backup-agent
docker compose pull
docker compose up -d
```

## Диагностика

```bash
docker logs -f hexaveil-backup-agent
docker compose -f /opt/hexaveil-backup-agent/docker-compose.yml ps
curl -s -H "Authorization: Bearer $AGENT_TOKEN" \
  "$AGENT_URL/api/backup-agent/v1/state" | head
```

Типовые причины:

| Симптом | Причина |
|---------|---------|
| `401` | токен перевыпущен в CMS — переустановите агента |
| агент `offline` в UI | нет исходящего HTTPS до CMS, проверьте firewall |
| `spool_bytes` растёт | CMS/хранилища недоступны, артефакты копятся локально |
| `pg_dump failed` | контейнер БД переименован — обновите рецепт |

## Удаление

```bash
cd /opt/hexaveil-backup-agent
docker compose down
docker volume rm hexaveil-backup-agent_agent_spool
rm -rf /opt/hexaveil-backup-agent
```
