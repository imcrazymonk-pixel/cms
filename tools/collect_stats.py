#!/usr/bin/env python3
"""
MonoList Node Statistics Collector
Usage:
  python3 collect_stats.py                          # JSON → stdout
  python3 collect_stats.py --save ../nodes_stats.json  # сохранить в файл
  python3 collect_stats.py --cache 30               # кэш 30 сек (файл nodes_stats.json)

Требования: ssh-ключи настроены для всех нод (~/.ssh/config или ssh-mcp-hosts.json)
Ноды подключаются по очереди, каждая за ~3-5 сек.
"""

import json, subprocess, sys, os, re, socket, struct, time
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────
# КОНФИГУРАЦИЯ НОД
# ──────────────────────────────────────────────────────────────────────
NODES = [
    {"id": "yandex",  "name": "Yandex CDN",   "host": "155.212.131.4",  "port": 356,  "user": "kilo"},
    {"id": "ru",      "name": "RU YouTube",     "host": "159.194.221.84", "port": 356,  "user": "kilo"},
    {"id": "de",      "name": "DE Files (origin)", "host": "144.31.96.78", "port": 356,  "user": "kilo"},
    {"id": "fi",      "name": "FI Audio",       "host": "31.77.128.251",  "port": 356,  "user": "kilo"},
    {"id": "nl",      "name": "NL Photo",       "host": "150.241.94.61",  "port": 356,  "user": "kilo"},
    {"id": "us",      "name": "US Data",        "host": "162.217.248.186","port": 356,  "user": "kilo"},
]

# Пинги — цели для замеров с каждой ноды
PING_TARGETS = [
    ("8.8.8.8",         "Google DNS"),
    ("77.88.8.8",       "Яндекс DNS"),
    ("ya.ru",           "Яндекс (Москва)"),
    ("vk.com",          "VK (СПб)"),
    ("144.31.96.78",    "DE (files)"),
    ("144.31.156.172",  "Панель"),
    ("31.77.128.251",   "FI (audio)"),
    ("150.241.94.61",   "NL (photo)"),
    ("159.194.221.84",  "RU (video)"),
    ("162.217.248.186", "US (data)"),
    ("155.212.131.4",   "Yandex"),
]

SPEED_TEST_URL = "http://speedtest.tele2.net/100MB.zip"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "nodes_stats.json")
CACHE_SECONDS = 0  # переопределяется --cache
SAVE_TO_FILE = None

# ──────────────────────────────────────────────────────────────────────

def ssh(host, port, user, cmd, timeout=15):
    """Выполнить команду на ноде через SSH, вернуть stdout."""
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no",
             "-o", f"ConnectTimeout={timeout}",
             "-o", "BatchMode=yes",
             "-p", str(port),
             f"{user}@{host}", cmd],
            capture_output=True, text=True, timeout=timeout + 5)
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", 124
    except Exception as e:
        return f"SSH Error: {e}", -1

def parse_ping(line):
    """Из строки ping вытащить ms, loss."""
    ms = loss = None
    m = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)', line)
    if m: ms = round(float(m.group(1)), 1)
    m = re.search(r'(\d+)% packet loss', line)
    if m: loss = int(m.group(1))
    return ms, loss

def parse_uptime(line):
    m = re.search(r'up\s+(.+?),\s+\d+\s+user', line)
    return m.group(1) if m else line

def collect_node(node):
    """Собрать данные с одной ноды, вернуть dict."""
    host, port, user = node["host"], node["port"], node["user"]
    result = {"id": node["id"], "name": node["name"], "host": host, "port": port,
              "reachable": False, "error": None, "data": {}}

    # ── базовая проверка ──
    out, rc = ssh(host, port, user, "echo OK")
    if rc != 0 or "OK" not in out:
        result["error"] = out[:200] if out else "Connection failed"
        return result
    result["reachable"] = True

    # ── hostname + uptime ──
    out, _ = ssh(host, port, user, "hostname && echo '---' && uptime")
    lines = out.split("\n---\n")
    result["data"]["hostname"] = lines[0].strip() if lines else ""
    result["data"]["uptime_raw"] = lines[1].strip() if len(lines) > 1 else ""
    result["data"]["uptime"] = parse_uptime(lines[1]) if len(lines) > 1 else ""

    # ── load average ──
    out, _ = ssh(host, port, user, "cat /proc/loadavg | awk '{print $1, $2, $3}'")
    parts = out.strip().split()
    result["data"]["load"] = {"1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])} if len(parts) >= 3 else {}

    # ── CPU cores ──
    out, _ = ssh(host, port, user, "nproc")
    result["data"]["cpu_cores"] = int(out.strip()) if out.strip().isdigit() else 0

    # ── RAM ──
    out, _ = ssh(host, port, user, "free -h | grep Mem")
    m = re.search(r'Mem:\s+(\S+)\s+(\S+)\s+(\S+)', out)
    if m:
        result["data"]["ram"] = {"total": m.group(1), "used": m.group(2), "free": m.group(3)}

    # ── DISK ──
    out, _ = ssh(host, port, user, "df -h / | tail -1")
    parts = out.strip().split()
    if len(parts) >= 5:
        result["data"]["disk"] = {"total": parts[1], "used": parts[2], "free": parts[3], "pct": parts[4]}

    # ── Docker ──
    out, _ = ssh(host, port, user, 'docker ps --format "{{.Names}}\t{{.Status}}\t{{.Image}}" 2>/dev/null')
    containers = []
    for ln in out.strip().split("\n"):
        p = ln.split("\t")
        if len(p) >= 3:
            containers.append({"name": p[0], "status": p[1], "image": p[2]})
    result["data"]["docker"] = containers

    # ── nginx test ──
    out, _ = ssh(host, port, user, "nginx -t 2>&1; echo '---EXIT---'; docker exec nginx-selfsteal nginx -t 2>&1 2>/dev/null")
    nginx_status = "unknown"
    if "successful" in out:
        nginx_status = "ok"
    elif "failed" in out or "emerg" in out or "Permission denied" in out:
        nginx_status = "error"
    err_line = ""
    for ln in out.split("\n"):
        if "emerg" in ln or "Permission denied" in ln:
            err_line = ln.strip()
            break
    result["data"]["nginx"] = {"status": nginx_status, "error": err_line if err_line else None}
    out2, _ = ssh(host, port, user, "systemctl is-active nginx 2>/dev/null")
    result["data"]["nginx_systemd"] = out2.strip() if out2.strip() and "not" not in out2 else "inactive"

    # ── Network errors ──
    out, _ = ssh(host, port, user, "ip -s link show eth0 2>/dev/null | tail -5")
    errs = {"rx_err": None, "rx_drop": None, "tx_err": None, "tx_drop": None}
    m = re.search(r'RX:\s+.*?errors\s+(\d+)', out)
    if m: errs["rx_err"] = int(m.group(1))
    m = re.search(r'dropped\s+(\d+)', out)
    if m: errs["rx_drop"] = int(m.group(1))
    result["data"]["network_errors"] = errs

    # ── TCP Statistics ──
    out, _ = ssh(host, port, user, "nstat -az TcpRetransSegs TcpExtTCPTimeouts TcpInSegs TcpOutSegs 2>/dev/null")
    tcp = {}
    for ln in out.split("\n"):
        if ln.startswith("TcpRetransSegs"):
            tcp["retrans"] = int(ln.split()[1])
        elif ln.startswith("TcpExtTCPTimeouts"):
            tcp["timeouts"] = int(ln.split()[1])
        elif ln.startswith("TcpInSegs"):
            tcp["in_segs"] = int(ln.split()[1])
        elif ln.startswith("TcpOutSegs"):
            tcp["out_segs"] = int(ln.split()[1])
    if tcp.get("out_segs", 0) > 0:
        tcp["retrans_pct"] = round(tcp["retrans"] / tcp["out_segs"] * 100, 2)
    result["data"]["tcp"] = tcp

    # ── Сертификаты ──
    out, _ = ssh(host, port, user,
        'for f in /opt/nginx-selfsteal/ssl/fullchain.crt /etc/letsencrypt/live/*/fullchain.pem /etc/nginx/ssl/*/fullchain.pem; do '
        '[ -f "$f" ] && echo "$f|$(openssl x509 -in "$f" -noout -enddate 2>/dev/null)"; done')
    certs = []
    for ln in out.strip().split("\n"):
        if "|" in ln:
            parts = ln.split("|")
            certs.append({"path": parts[0], "expiry": parts[1].replace("notAfter=", "")})
    result["data"]["certs"] = certs

    # ── Speedtest ──
    out, _ = ssh(host, port, user,
        f'curl -o /dev/null -s -w "%{{speed_download}}" --max-time 12 {SPEED_TEST_URL} 2>/dev/null')
    if out.strip() and out.strip().replace(".", "").isdigit():
        bps = float(out.strip())
        result["data"]["speed_download_bps"] = int(bps)
        result["data"]["speed_download_mbps"] = round(bps / 1e6, 1)
    else:
        result["data"]["speed_download_mbps"] = 0

    # ── Pings ──
    pings = {}
    for target, label in PING_TARGETS:
        out, _ = ssh(host, port, user, f"ping -c 2 -w 4 {target} 2>&1 | tail -1")
        ms, loss = parse_ping(out)
        if ms is not None or loss is not None:
            pings[target] = {"ms": ms, "loss": loss, "label": label}
    result["data"]["pings"] = pings

    return result

def collect_all():
    """Собрать данные со всех нод."""
    results = {"collected_at": datetime.utcnow().isoformat() + "Z", "nodes": []}
    for node in NODES:
        print(f"⏳ {node['name']}...", file=sys.stderr)
        try:
            data = collect_node(node)
            results["nodes"].append(data)
            status = "✅" if data["reachable"] else "❌"
            print(f"  {status} {data.get('data', {}).get('hostname', 'N/A')} ({data.get('error', 'ok')})", file=sys.stderr)
        except Exception as e:
            print(f"  ❌ {node['name']}: {e}", file=sys.stderr)
            results["nodes"].append({"id": node["id"], "name": node["name"], "host": node["host"],
                                      "reachable": False, "error": str(e), "data": {}})
    return results

if __name__ == "__main__":
    # Парсинг аргументов
    args = sys.argv[1:]
    if "--save" in args:
        idx = args.index("--save") + 1
        if idx < len(args):
            SAVE_TO_FILE = args[idx]
    if "--cache" in args:
        idx = args.index("--cache") + 1
        if idx < len(args):
            CACHE_SECONDS = int(args[idx])

    # Проверка кэша
    cache_path = SAVE_TO_FILE or CACHE_FILE
    if CACHE_SECONDS > 0 and os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        if time.time() - mtime < CACHE_SECONDS:
            with open(cache_path) as f:
                print(f.read())
            sys.exit(0)

    # Сбор
    data = collect_all()
    output = json.dumps(data, ensure_ascii=False, indent=2)

    # Сохранение
    if SAVE_TO_FILE:
        os.makedirs(os.path.dirname(os.path.abspath(SAVE_TO_FILE)), exist_ok=True)
        with open(SAVE_TO_FILE, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to {SAVE_TO_FILE}", file=sys.stderr)
    elif CACHE_SECONDS > 0:
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(output)

    print(output)