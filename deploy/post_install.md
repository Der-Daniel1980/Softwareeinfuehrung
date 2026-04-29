# SysIntro – Admin-Handbuch

## Admin-Passwort ändern

Das Standard-Passwort lautet `admin@demo.local / demo1234`.  
Passwort zurücksetzen (setzt auf `demo1234` zurück):

```bash
cd /opt/sysintro/app
sudo -u sysintro /opt/sysintro/venv/bin/python -m app.seed.run_seed --reset-admin-password
```

Danach direkt im Web-Interface unter **Profil → Passwort ändern** ein eigenes Passwort setzen.

> **Hinweis:** Das Seed-Skript akzeptiert kein eigenes Passwort als Argument —
> es setzt immer auf `demo1234` zurück. Das endgültige Passwort muss über die
> Weboberfläche gesetzt werden.

---

## Log-Dateien

| Was | Befehl |
|-----|--------|
| App-Log (live) | `journalctl -u sysintro -f` |
| App-Log (letzte 100 Zeilen) | `journalctl -u sysintro -n 100 --no-pager` |
| nginx Access-Log | `tail -f /var/log/nginx/access.log` |
| nginx Error-Log  | `tail -f /var/log/nginx/error.log` |

---

## Update (neue Version einspielen)

1. Quellcode im Repo aktualisieren (z. B. `git pull`).
2. Installer erneut ausführen — er ist idempotent:

```bash
sudo bash /opt/sysintro/app/deploy/install.sh
```

Die `.env`-Datei wird dabei **nicht** überschrieben.  
Neue Migrations werden automatisch per `alembic upgrade head` angewendet.

---

## Datenbank sichern

Die SQLite-Datenbank liegt unter:

```
/opt/sysintro/data/sysintro.db
```

**Online-Backup** (ohne Service-Stop, WAL-sicher):

```bash
sqlite3 /opt/sysintro/data/sysintro.db ".backup '/root/sysintro_backup_$(date +%F).db'"
```

**Automatische tägliche Sicherung** (cron-Beispiel für root):

```cron
0 3 * * * sqlite3 /opt/sysintro/data/sysintro.db ".backup '/root/backups/sysintro_$(date +\%F).db'"
```

---

## Demo-Benutzer deaktivieren

1. Als Admin einloggen.
2. Menü: **Admin → Benutzer** (`/admin/users`).
3. Jeden Demo-Benutzer auswählen und auf **Deaktivieren** klicken.

---

## TLS nachträglich aktivieren

Voraussetzung: Domain ist im DNS auf den Server gezeigt und Port 80/443 ist offen.

```bash
sudo SYSINTRO_TLS=1 SYSINTRO_DOMAIN=sysintro.example.com \
     bash /opt/sysintro/app/deploy/install.sh \
     --domain sysintro.example.com --tls
```

Certbot beschafft automatisch ein Let's-Encrypt-Zertifikat und passt die nginx-Konfiguration an.

---

## Troubleshooting

### Service startet nicht

```bash
systemctl status sysintro
journalctl -u sysintro -n 50 --no-pager
```

Häufige Ursachen:
- Fehler in `/opt/sysintro/.env` (z. B. `SECRET_KEY` fehlt)
- Datenbank-Pfad nicht erreichbar (Berechtigungen prüfen: `ls -la /opt/sysintro/data/`)
- Python-Abhängigkeit fehlt → `sudo -u sysintro /opt/sysintro/venv/bin/pip check`

### nginx-Fehler (502 Bad Gateway)

Prüfen ob uvicorn läuft:

```bash
systemctl status sysintro
ss -tlnp | grep 8080
```

### nginx-Konfigurationsfehler

```bash
nginx -t
journalctl -u nginx -n 30 --no-pager
```

### .env neu generieren

Falls die `.env` beschädigt ist, kann sie manuell gelöscht und der Installer erneut
ausgeführt werden — er erstellt dann eine neue Datei:

```bash
rm /opt/sysintro/.env
sudo bash /opt/sysintro/app/deploy/install.sh
```

### Service manuell neu starten

```bash
systemctl restart sysintro
systemctl reload nginx
```
