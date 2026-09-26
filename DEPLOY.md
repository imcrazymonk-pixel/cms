# Deploy HexaVeil CMS (standalone server)

CMS ставится на отдельный сервер, Nginx слушает 80-й порт напрямую.

## 1. Подготовка сервера

```bash
# Подключиться
ssh root@твой-сервер

# Установить Docker (если нет)
curl -fsSL https://get.docker.com | sh
```

## 2. Скопировать проект

```bash
# На сервере
mkdir -p /opt/HexaVeil_CMS
cd /opt/HexaVeil_CMS
```

**Вариант A — через git:**
```bash
git clone <url-репозитория> .
```

**Вариант B — через rsync с локальной машины:**
```bash
# На локальной машине
rsync -avz --exclude '.git' --exclude 'Fin/' --exclude '__pycache__' \
  /путь/к/NewWeb/ root@твой-сервер:/opt/HexaVeil_CMS/
```

## 3. Настроить .env

На сервере два IP:
- **Старый** — на нём уже висит заглушка ноды (не трогать)
- **Новый** — выдал хостер, сюда сажаем CMS

```bash
cd /opt/HexaVeil_CMS

cp .env.prod .env
nano .env
```

**Что обязательно поменять:**

```ini
# IP, который выдал хостер для CMS
CMS_BIND_IP=5.5.5.5     # <-- заменить на свой новый IP

# Пароль БД — придумать свой
DB_PASS=надёжный_пароль

# Ключ шифрования (сгенерировать!)
APP_ENCRYPTION_KEY=здесь_64_hex_символа

# Email админа
ADMIN_EMAIL=admin@твой-сайт.ru
```

**Сгенерировать ключ:**
```bash
openssl rand -hex 32
# Результат вставить в APP_ENCRYPTION_KEY
```

## 4. Запустить

```bash
cd /opt/HexaVeil_CMS

# Production compose
cp docker-compose.prod.yml docker-compose.yml

# Запустить
docker compose up -d

# Проверить
docker compose ps
docker compose logs app

# Открыть в браузере
curl http://твой-сервер
# Должен показать HTML лендинга HexaVeil
```

## 5. Настроить HTTPS (Certbot)

```bash
# Установить certbot
apt install -y certbot

# Получить сертификат (Nginx должен быть на 80 порту)
certbot certonly --standalone -d hexacms.твой-сайт.ru

# Скопировать сертификаты
mkdir -p /opt/HexaVeil_CMS/ssl
cp /etc/letsencrypt/live/hexacms.твой-сайт.ru/fullchain.pem /opt/HexaVeil_CMS/ssl/
cp /etc/letsencrypt/live/hexacms.твой-сайт.ru/privkey.pem /opt/HexaVeil_CMS/ssl/
```

**Добавить HTTPS в Nginx конфиг** `.docker/nginx/default.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name hexacms.твой-сайт.ru;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    # ... остальной конфиг такой же как для 80 порта
}

server {
    listen 80;
    server_name hexacms.твой-сайт.ru;
    return 301 https://$host$request_uri;
}
```

**Перезапустить:**
```bash
docker compose restart web
```

**Авто-обновление сертификата (cron):**
```bash
crontab -e
# Добавить строку (обновляется раз в месяц):
0 3 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/hexacms.твой-сайт.ru/fullchain.pem /opt/HexaVeil_CMS/ssl/ && cp /etc/letsencrypt/live/hexacms.твой-сайт.ru/privkey.pem /opt/HexaVeil_CMS/ssl/ && docker compose -f /opt/HexaVeil_CMS/docker-compose.yml restart web
```

## 6. Первый вход

- **Сайт**: `http://IP-сервера` (или `https://hexacms.твой-сайт.ru`)
- **Админка**: `/admin`
- **Логин**: `admin`
- **Пароль**: `admin12345`

## 7. Бекапы

```bash
# Бекап БД
docker compose exec -T db pg_dump -U cms -d cms > /opt/backups/cms_$(date +%Y%m%d).sql

# Восстановить
docker compose exec -T db psql -U cms -d cms < backup.sql

# Авто-бекап (cron)
0 2 * * * docker compose -f /opt/HexaVeil_CMS/docker-compose.yml exec -T db pg_dump -U cms -d cms | gzip > /opt/backups/cms_$(date +\%Y\%m\%d).sql.gz && find /opt/backups/ -name '*.sql.gz' -mtime +30 -delete
```

## 8. Обновление

```bash
cd /opt/HexaVeil_CMS

# Забрать новые файлы
git pull

# Пересобрать и перезапустить
docker compose up --build -d

# Проверить логи
docker compose logs -f
```