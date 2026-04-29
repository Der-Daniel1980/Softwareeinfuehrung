# Installation auf Ubuntu 26.04

Diese Anleitung beschreibt die Erstinstallation und das Update von SysIntro auf einer frischen Ubuntu-26.04-VM.

## Voraussetzungen

- **Ubuntu 26.04 LTS** (24.04 funktioniert ebenfalls; das Skript warnt nur)
- **root-Zugang** via SSH oder lokal
- Mindestens **1 GB RAM**, **2 GB Plattenplatz**
- Optional: eine **DNS-A-Record** auf den Server (Pflicht, wenn TLS aktiviert wird)

## Variante 1: Per Git-Clone (empfohlen)

```bash
# Auf dem Server als root:
apt-get update && apt-get install -y git
git clone https://github.com/Der-Daniel1980/Softwareeinfuehrung.git /tmp/sysintro
cd /tmp/sysintro
bash deploy/install.sh
```

Das Skript fragt interaktiv:
- Domain (z. B. `sysintro.example.com`, oder `_` für „beliebiger Host")
- Admin-E-Mail
- TLS aktivieren (j/n)

## Variante 2: Non-interaktiv per Env-Variablen

```bash
SYSINTRO_DOMAIN=sysintro.example.com \
SYSINTRO_ADMIN_EMAIL=it-admin@example.com \
SYSINTRO_TLS=1 \
bash deploy/install.sh --tls
```

Verfügbare Variablen / Flags:

| Env-Variable | Flag | Default | Bedeutung |
|---|---|---|---|
| `SYSINTRO_DOMAIN` | `--domain X` | `_` | nginx server_name |
| `SYSINTRO_ADMIN_EMAIL` | `--email X` | `admin@example.com` | für certbot + Reminder-Eskalation |
| `SYSINTRO_TLS` | `--tls` | `0` | TLS via Let's Encrypt |
| `SYSINTRO_HOME` | – | `/opt/sysintro` | Installationspfad |
| `SYSINTRO_ADMIN_PASSWORD` | `--admin-password X` | – | Hinweis-Flag (Demo: aktuell nur Reset auf `demo1234` möglich; Passwort-Wechsel via Web-UI nach Login) |
| – | `--no-firewall` | aus | ufw-Konfiguration überspringen |

## Was passiert bei der Installation

1. **System-Packages:** python3.12, python3-venv, nginx, sqlite3, ufw, openssl
2. **System-User** `sysintro` (no-login, system account)
3. **Verzeichnisse** unter `/opt/sysintro/`: `app/`, `data/`, `attachments/`, `logs/`, `venv/`
4. **Code-Sync** via rsync vom geclonten Repo nach `/opt/sysintro/app/`
5. **venv** + Python-Abhängigkeiten aus `requirements.txt`
6. **`.env`** wird einmalig generiert (mit zufälligem `SECRET_KEY`); bei Re-Installation NICHT überschrieben
7. **Migrationen** (`alembic upgrade head`) und **Seed** (Rollen, Demo-Benutzer, Felder)
8. **systemd-Unit** `/etc/systemd/system/sysintro.service` (mit Hardening: `NoNewPrivileges`, `ProtectSystem=strict`, etc.)
9. **nginx** als Reverse-Proxy auf Port 80; mit `--tls` zusätzlich Let's-Encrypt-Cert via certbot
10. **Firewall** (ufw) öffnet 22/80/443

## Nach der Installation

```bash
systemctl status sysintro          # Service läuft?
journalctl -u sysintro -f          # Logs live
curl http://localhost:8080/login   # interner Check (am Server)
```

Im Browser: `http(s)://<DEINE_DOMAIN>/login`

**Erste Anmeldung:**
- E-Mail: `admin@demo.local`
- Passwort: `demo1234`

> ⚠️ **Demo-Passwörter sind öffentlich dokumentiert.** Vor Produktiv-Nutzung in `/admin/users` neue Benutzer anlegen und alle `*@demo.local`-Konten deaktivieren.

## Update / Re-Deployment

Code aktualisieren und Skript erneut ausführen — es ist idempotent:

```bash
cd /tmp/sysintro
git pull
bash deploy/install.sh
```

Das Skript erhält dabei:
- Bestehende `.env` (kein Überschreiben)
- Datenbank-Inhalte (`/opt/sysintro/data/sysintro.db`)
- Bereits hochgeladene Anhänge (`/opt/sysintro/attachments/`)

Es ersetzt nur Code und führt neue Migrationen aus.

## Troubleshooting

### Service startet nicht

```bash
journalctl -u sysintro -n 50 --no-pager
```

Häufige Ursachen:
- `.env` fehlt → `ls -la /opt/sysintro/.env` (sollte 600 sysintro:sysintro gehören)
- Migrations-Fehler → `cd /opt/sysintro/app && sudo -u sysintro /opt/sysintro/venv/bin/alembic current`
- Port 8080 belegt → `ss -tlnp | grep 8080`

### nginx liefert 502 Bad Gateway

Service läuft nicht oder lauscht auf falschem Port. Test:

```bash
curl http://127.0.0.1:8080/login
```

Sollte HTML zurückliefern. Falls nicht, Service-Logs prüfen.

### Login mit Demo-Passwort schlägt fehl

```bash
sudo -u sysintro /opt/sysintro/venv/bin/python -m app.seed.run_seed --reset-admin-password
# Setzt admin@demo.local auf demo1234 zurück
```

### TLS-Cert konnte nicht erworben werden

- Domain muss per A-Record auf den Server zeigen
- Port 80 darf nicht von einer Firewall davor blockiert sein (Hetzner-Cloud hat eine eigene Firewall, nicht nur `ufw`)
- Erneut: `certbot --nginx -d $DOMAIN --redirect`

## Deinstallation

```bash
cd /tmp/sysintro
bash deploy/uninstall.sh --yes
```

Daten in `/opt/sysintro/data/` und `/opt/sysintro/attachments/` bleiben erhalten — manuell löschen mit `rm -rf /opt/sysintro` falls gewünscht.
