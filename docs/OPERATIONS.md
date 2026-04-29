# Betriebshandbuch

Anleitungen für den laufenden Betrieb von SysIntro auf Ubuntu.

## Service-Steuerung

```bash
systemctl status sysintro            # Status
systemctl restart sysintro           # Neustart (z. B. nach .env-Änderung)
systemctl stop sysintro              # Stoppen
systemctl disable sysintro           # Auto-Start deaktivieren
```

## Logs

### App-Logs

```bash
journalctl -u sysintro -f            # live
journalctl -u sysintro --since "1 hour ago"
journalctl -u sysintro -n 100        # letzte 100 Zeilen
```

Die App schreibt strukturiertes JSON-Logging über Python `logging` → systemd-journal.

### nginx-Logs

```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## Datenbank

### Größe prüfen

```bash
ls -lh /opt/sysintro/data/sysintro.db*
# .db-wal und .db-shm sind WAL-Mode-Hilfsdateien
```

### Inhalt prüfen

```bash
sudo -u sysintro sqlite3 /opt/sysintro/data/sysintro.db
sqlite> .tables
sqlite> SELECT COUNT(*) FROM application_requests;
sqlite> SELECT id, status, system_category FROM application_requests;
sqlite> .quit
```

### Backup

**Manuelles Hot-Backup** (sicher während Betrieb):

```bash
DATE=$(date +%F)
sudo -u sysintro sqlite3 /opt/sysintro/data/sysintro.db \
    ".backup /opt/sysintro/data/sysintro-${DATE}.db.bak"
```

**Cron-Job** (`/etc/cron.daily/sysintro-backup`):

```bash
#!/bin/bash
set -e
DATE=$(date +%F)
BACKUP_DIR=/var/backups/sysintro
mkdir -p "$BACKUP_DIR"
sudo -u sysintro sqlite3 /opt/sysintro/data/sysintro.db ".backup ${BACKUP_DIR}/sysintro-${DATE}.db"
# Anhänge mitsichern
tar -czf "${BACKUP_DIR}/attachments-${DATE}.tgz" -C /opt/sysintro attachments/
# Alte Backups (>30 Tage) löschen
find "$BACKUP_DIR" -name "sysintro-*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "attachments-*.tgz" -mtime +30 -delete
```

```bash
chmod +x /etc/cron.daily/sysintro-backup
```

### Restore

```bash
systemctl stop sysintro
cp /var/backups/sysintro/sysintro-2026-04-29.db /opt/sysintro/data/sysintro.db
chown sysintro:sysintro /opt/sysintro/data/sysintro.db
systemctl start sysintro
```

## Updates

```bash
cd /tmp/sysintro            # oder wo das Repo liegt
git pull
bash deploy/install.sh      # idempotent
```

`install.sh` führt automatisch `alembic upgrade head` aus — neue Migrationen werden angewandt.

## Reminder-Engine

### Funktionsweise

APScheduler innerhalb des Uvicorn-Prozesses startet beim App-Start einen täglichen Cron-Job (`scheduler.py`). Bei Unklarheit / Demo manuell triggern:

**Web-UI:** Admin-Dashboard → Button „Reminder-Scan jetzt ausführen"

**API:** `POST /api/v1/admin/run-reminder-scan` (mit Admin-Cookie)

### Frequenz / Stufen ändern

In `app/services/reminders.py`:

```python
STAGE_1_DAYS = 3
STAGE_2_DAYS = 7
STAGE_3_DAYS = 14
```

Nach Änderung Service neustarten.

### Kein echter Mail-Versand in der Demo

Reminder werden in der Tabelle `notifications` protokolliert, aber NICHT versendet. Inhalt einsehbar via:

```bash
sudo -u sysintro sqlite3 /opt/sysintro/data/sysintro.db \
    "SELECT id, kind, recipient_email, subject, would_send_at FROM notifications ORDER BY id DESC LIMIT 20;"
```

Für echten Versand: `app/services/mailer.py::would_send()` durch SMTP-Client ersetzen (z. B. `aiosmtplib`).

## Benutzer-Management

### Demo-Benutzer deaktivieren

Im Web-UI als Admin: `/admin/users` → Benutzer auswählen → „Deaktivieren". Empfohlen vor Produktiv-Nutzung.

### Per CLI

```bash
sudo -u sysintro sqlite3 /opt/sysintro/data/sysintro.db \
    "UPDATE users SET is_active=0 WHERE email LIKE '%@demo.local';"
```

### Admin-Passwort zurücksetzen

```bash
cd /opt/sysintro/app
sudo -u sysintro /opt/sysintro/venv/bin/python -m app.seed.run_seed --reset-admin-password
# → admin@demo.local hat wieder Passwort "demo1234"
# danach im Web-UI ändern!
```

## TLS / Zertifikate

### Erstmalige Aktivierung

```bash
SYSINTRO_DOMAIN=meinedomain.de SYSINTRO_TLS=1 \
    bash deploy/install.sh --tls
```

Schreibt `SECURE_COOKIES=1` in `.env` und führt certbot aus.

### Erneuerung

certbot legt einen Cron-Job an (`/etc/cron.d/certbot`). Manuell prüfen:

```bash
certbot renew --dry-run
```

### Domain-Wechsel

```bash
sed -i 's/old.example.com/new.example.com/g' /etc/nginx/sites-available/sysintro
nginx -t && systemctl reload nginx
certbot --nginx -d new.example.com
```

## Performance

### Aktuelle Demo-Architektur

Single-uvicorn-Worker + SQLite. Reicht für **bis ca. 20 gleichzeitige aktive Benutzer** auf einer kleinen VM (1 vCPU, 1 GB RAM).

### Skalierung über die Demo hinaus

1. **Postgres** statt SQLite (Alembic-DSN ändern, neu migrieren)
2. **Mehr Worker:** im Service `--workers 4` (geht nur mit Postgres, da SQLite single-writer)
3. **Reminder-Worker** auslagern: Celery + Redis statt APScheduler

## Health-Check

```bash
curl -fsS http://localhost:8080/api/v1/auth/me
# 401 = OK (Service antwortet, Auth wird verlangt)
# Connection refused = Service down
```

Externer Monitoring-Endpoint: `GET /api/v1/auth/me` mit gültigem Cookie liefert `200`. Ohne Cookie `401`.
Für reines Health-Probing reicht: `curl -fsS http://localhost:8080/login` → `200`.

## Disaster-Recovery (DR)

| Szenario | Procedure |
|---|---|
| App startet nicht | `journalctl -u sysintro -n 100` → Fehler diagnostizieren; oft `.env` korrupt → aus `.env.example` neu generieren, `SECRET_KEY` neu setzen |
| DB korrupt | `sqlite3 .recover` oder Restore aus letztem Backup |
| Disk voll | `du -sh /opt/sysintro/* /var/log/* /var/backups/*` → alte Backups oder Logs prüfen |
| Falscher Code deployed | `git checkout <prev-commit> && bash deploy/install.sh` |

## Monitoring (produktiv ergänzen)

Nicht in der Demo enthalten — Empfehlung:

- **Prometheus + Grafana** für Metriken (`fastapi-prometheus` lib)
- **Loki** für Log-Aggregation
- **Uptime-Kuma** für Externes Health-Probing
- Alerts bei: Service-Restart, 5xx-Rate, DB-Größe-Threshold, Reminder-Stufe-3-Eskalationen
