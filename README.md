# SysIntro

**Digitalisierter Systemeinführungs- und Freigabeprozess (Demo)**

SysIntro ersetzt den bisherigen Excel-basierten Prozess zur Systemeinführung und -änderung bei amedes durch eine Webanwendung mit revisionssicherem Audit-Trail, mehrstufiger Freigabe durch sechs Fachbereiche und einem zentralen Applikationsverzeichnis.

> **Demo-Hinweis:** Diese Version ist ein lauffähiger Prototyp zur Konzept-Validierung. Sie deckt den Kernworkflow vollständig ab; produktive Härtung (SSO/Keycloak, MFA, echter SMTP-Versand, PDF-Export, vollständige Internationalisierung) ist in der Spec für Phase 2/3 vorgesehen — siehe [`SPEC.md`](SPEC.md).

---

## Inhalt der Doku

| Datei | Inhalt |
|---|---|
| [README.md](README.md) (diese Datei) | Überblick, Quick-Start, Tech-Stack |
| [SPEC.md](SPEC.md) | Vollständiges Fachkonzept (Auftraggeberdokument) |
| [CLAUDE.md](CLAUDE.md) | Coding-Konventionen für Beitragende |
| [docs/INSTALL.md](docs/INSTALL.md) | Installation auf Ubuntu 26.04 (Schritt für Schritt) |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Anwender-Handbuch (deutsch) — Antragsteller, Reviewer, Admin |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architektur, Datenmodell, Workflow-State-Machine |
| [docs/API.md](docs/API.md) | REST-API-Referenz, Auth-Flow |
| [docs/SECURITY.md](docs/SECURITY.md) | Sicherheits-Konzept und Härtungs-Checkliste |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Betrieb: Logs, Backups, Updates, Reminder-Engine |
| [deploy/post_install.md](deploy/post_install.md) | Admin-Kurzleitfaden direkt nach Installation |

---

## Quick-Start (lokal)

```bash
# 1) Abhängigkeiten
python -m venv .venv
source .venv/bin/activate          # Windows:  .venv\Scripts\activate
pip install -r requirements.txt

# 2) Konfiguration
cp .env.example .env
# .env editieren: SECRET_KEY auf einen langen Zufallswert setzen

# 3) Datenbank anlegen + Demo-Daten einspielen
alembic upgrade head
python -m app.seed.run_seed

# 4) Server starten
uvicorn app.main:app --reload

# Browser: http://localhost:8000/login
```

### Demo-Zugänge (Passwort `demo1234`)

| E-Mail | Rolle | Verwendungszweck |
|---|---|---|
| `admin@demo.local` | ADMIN | Benutzerverwaltung, Audit, Reminder-Scan |
| `requester@demo.local` | REQUESTER | Antrag erstellen |
| `owner@demo.local` | REQUESTER | wird als Application Owner ausgewählt |
| `br@demo.local` | BETRIEBSRAT | Mitbestimmungs-Freigaben |
| `itsec@demo.local` | IT_SECURITY | Sicherheits-Freigaben |
| `dsb@demo.local` | DATA_PROTECTION | Datenschutz-Freigaben |
| `appmgr@demo.local` | APP_MANAGER | Fachliche Freigaben |
| `appop@demo.local` | APP_OPERATION | Betriebs-Freigaben |
| `lic@demo.local` | LICENSE_MGMT | Lizenz-/Kosten-Freigaben |
| `auditor@demo.local` | AUDITOR | Read-only auf Audit-Log und Verzeichnis |

---

## Server-Installation (Ubuntu 26.04)

```bash
# Auf dem Server als root:
git clone https://github.com/Der-Daniel1980/Softwareeinfuehrung.git /tmp/sysintro
cd /tmp/sysintro
bash deploy/install.sh                # interaktiv
# oder non-interaktiv:
SYSINTRO_DOMAIN=meinedomain.de SYSINTRO_TLS=1 \
SYSINTRO_ADMIN_EMAIL=admin@meinedomain.de \
bash deploy/install.sh --tls
```

Nach dem Skript:
- App läuft unter `http(s)://<DOMAIN>`
- Service: `systemctl status sysintro`
- Logs: `journalctl -u sysintro -f`
- App-Verzeichnis: `/opt/sysintro/`

Vollständige Anleitung mit Troubleshooting → [`docs/INSTALL.md`](docs/INSTALL.md).

---

## Tech-Stack

| Schicht | Wahl |
|---|---|
| Backend | FastAPI 0.115, Python 3.11+ |
| Datenbank | SQLite 3 (WAL-Modus) |
| ORM / Migrations | SQLAlchemy 2.x, Alembic |
| Auth | JWT in HttpOnly-Cookie, Argon2 (`argon2-cffi`) |
| Hintergrundjobs | APScheduler (in-process) |
| Frontend | Jinja2 + Tailwind CSS (CDN) + HTMX |
| Tests | pytest, freezegun, httpx |
| Linter | ruff |
| Deployment | systemd + nginx + ufw, install.sh |

**Bewusst nicht gewählt für Demo:** Postgres, Redis, Node-Build-Kette, Docker. Alles via einem Python-Prozess + einer SQLite-Datei. Migration auf Postgres ist über Alembic-DSN-Wechsel möglich.

---

## Funktionsumfang

- **Antragsworkflow** mit 14 Sektionen (Stammdaten, Systemkategorie A–D, Produkt, Anwendung, Datenschutz, Lizenzen, Betrieb, Cloud, SLA, Kosten, …)
- **Field-Responsibility-Matrix:** pro Feld pro Rolle entweder Information (I) oder Freigabe (F) — direkt aus der Excel-Vorlage übernommen
- **Sechs Freigabe-Rollen** mit ODER-Verknüpfung pro Rolle (eine Freigabe pro Rolle reicht)
- **Systemkategorie A–D** mit unterschiedlichen Workflow-Pfaden (BV-Anhang bei C, Vier-Augen-Notfall bei D)
- **Revisionierung** auf Feldebene + Vollsnapshot bei jedem Submit
- **Append-only Audit-Log** für Compliance
- **Reminder-Engine** mit 3 Eskalationsstufen (3/7/14 Tage)
- **Applikationsverzeichnis** inkl. Bestandsimport und CSV-Export
- **Rollenbasiertes Dashboard** mit altersbasierter Hervorhebung offener Freigaben

Details zum Workflow → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Tests

```bash
pytest -x                 # alle 50 Tests
pytest -x tests/test_workflow.py             # nur Workflow-Tests
pytest -x tests/smoke/                        # nur Smoke-Tests der Web-Pages
ruff check .                                  # Linter
```

Aktueller Stand: **50/50 Tests grün**, ruff clean.

---

## Lizenz / Eigentum

Demo-Code im Auftrag der amedes-Gruppe. Spec in [`SPEC.md`](SPEC.md). Code-Lizenz: TBD nach Abstimmung mit Auftraggeber.
