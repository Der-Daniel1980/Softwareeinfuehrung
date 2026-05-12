# SysIntro – Go-Live Plan

*Stand: 2026-05-12 · Ziel-Go-Live: Q3 2026*

Dieses Dokument beschreibt die technische Vorbereitung für den produktiven
Betrieb. Es deckt vier Bausteine ab:

1. [Authentifizierung über Keycloak (OIDC)](#1-keycloak-anbindung)
2. [Datenbankwechsel SQLite → PostgreSQL](#2-postgresql-migration)
3. [Mail-Versand](#3-mail-versand)
4. [Betrieb, Backup, Monitoring](#4-betrieb-und-backup)

Jeder Baustein hat: **Soll-Architektur · Umsetzungsschritte · Test-Plan ·
Rollback-Strategie.**

---

## 1. Keycloak-Anbindung

### 1.1 Ziel

- Einheitliches SSO über amedes-Keycloak.
- Antragsteller, Reviewer und Admins melden sich mit ihrem
  amedes-Account an (gleiche Credentials wie bei Outlook etc.).
- Rollen kommen als Keycloak-Realm-Roles oder per Group-Mapping.
- Logout in SysIntro beendet auch die Keycloak-Session
  (RP-initiated Logout).

### 1.2 Soll-Architektur

```
   Browser ─── HTTPS ───▶ SysIntro (FastAPI)
      ▲                       │
      │ 1. /login Redirect    │ 2. /auth/oidc/login → Keycloak /auth
      │                       ▼
      │           ┌───────────────────────────┐
      │           │  Keycloak amedes Realm    │
      │           │  Client: sysintro-web     │
      │           │  Flow:    Code + PKCE     │
      │           └───────────────────────────┘
      │                       │ 3. Redirect mit code
      ▼                       │
   /auth/oidc/callback ◀──────┘
      │ 4. Code → Tokens (Backend-Channel)
      │ 5. id_token validieren, JIT-User-Sync, Session-Cookie setzen
      ▼
   /requests …
```

### 1.3 Implementierung

**Bibliothek:** `authlib` (FastAPI-Integration, OIDC mit PKCE,
JWKS-Caching, ID-Token-Validierung „out-of-the-box").

**Neue Konfiguration (`app/core/config.py`):**

```python
AUTH_MODE: Literal["local", "oidc"] = "local"  # umschaltbar

# Nur bei AUTH_MODE=oidc relevant
OIDC_ISSUER: str = ""            # z. B. https://idp.amedes.de/realms/amedes
OIDC_CLIENT_ID: str = ""         # sysintro-web
OIDC_CLIENT_SECRET: str = ""     # nur Backend-Channel
OIDC_REDIRECT_URI: str = ""      # https://sysintro.amedes.de/auth/oidc/callback
OIDC_SCOPES: str = "openid profile email"
OIDC_ROLE_CLAIM: str = "realm_access.roles"  # Pfad zum Rollen-Claim
OIDC_ROLE_MAP: dict[str, str] = {            # KC-Rolle → SysIntro-Rolle-Code
    "sysintro-requester":      "REQUESTER",
    "sysintro-br":             "BETRIEBSRAT",
    "sysintro-it-security":    "IT_SECURITY",
    "sysintro-data-protection":"DATA_PROTECTION",
    "sysintro-app-manager":    "APP_MANAGER",
    "sysintro-app-operation":  "APP_OPERATION",
    "sysintro-license-mgmt":   "LICENSE_MGMT",
    "sysintro-admin":          "ADMIN",
}
```

**Neue Routen (`app/web/auth_oidc.py`):**

| Route | Zweck |
|---|---|
| `GET /auth/oidc/login` | Startet Auth-Code-Flow mit PKCE, Redirect zu KC `/auth`. |
| `GET /auth/oidc/callback` | Tauscht Code gegen Tokens, validiert `id_token` über JWKS, ruft JIT-Sync auf. |
| `GET /auth/oidc/logout` | RP-initiated Logout: löscht App-Session-Cookie + leitet auf `end_session_endpoint` weiter. |

**JIT-User-Provisioning (`app/services/auth_oidc.py`):**

```python
def sync_user_from_claims(db, claims) -> User:
    # 1. User per `sub` ODER `email` finden, sonst neu anlegen
    # 2. name, email aus claims aktualisieren
    # 3. Rollen aus claims['realm_access']['roles'] über OIDC_ROLE_MAP
    #    mappen, fehlende Role-Rows ergänzen, entfernte abziehen
    # 4. password_hash bleibt leer – User kann sich nicht mehr lokal anmelden
    # 5. last_login_at setzen
```

**Login-Seite (`app/templates/login.html`):**

- Bei `AUTH_MODE=oidc`: nur „Mit amedes-Konto anmelden"-Button →
  Redirect auf `/auth/oidc/login`.
- Bei `AUTH_MODE=local`: bisheriges Formular bleibt aktiv (für lokale
  Tests).
- Mischbetrieb für Notfall-Admin denkbar (Feature-Flag pro User-Eintrag).

**Was bleibt gleich:**

- Session-Cookie (JWT, HttpOnly, SameSite=Lax) bleibt das Auth-Token
  innerhalb der App – Keycloak liefert nur die Identität.
- CSRF, Rate-Limit, Audit-Log unverändert.
- Bestehende `User`-Tabelle wird wiederverwendet, nur `password_hash`
  wird optional (`NULL` bei reinen OIDC-Usern).

### 1.4 Keycloak-Realm-Konfiguration (Soll)

| Setting | Wert |
|---|---|
| Realm | `amedes` |
| Client-ID | `sysintro-web` |
| Client-Typ | Confidential (Backend-Channel) |
| Standard-Flow | Authorization Code + **PKCE** (S256) |
| Valid Redirect URIs | `https://sysintro.amedes.de/auth/oidc/callback` |
| Valid Post-Logout URIs | `https://sysintro.amedes.de/login` |
| Web-Origins | `https://sysintro.amedes.de` |
| Realm-Roles | `sysintro-requester`, `sysintro-br`, `sysintro-it-security`, `sysintro-data-protection`, `sysintro-app-manager`, `sysintro-app-operation`, `sysintro-license-mgmt`, `sysintro-admin` |
| Token-Lifespan | Access: 5 min · Refresh: 30 min · SSO Session Idle: 8 h |
| Default-ID-Token-Claims | `email`, `email_verified`, `preferred_username`, `name`, `realm_access.roles` |

### 1.5 Test-Plan

1. Lokal: Keycloak in Docker hochfahren, Test-Realm mit drei Demo-Usern
   (je Antragsteller, Reviewer, Admin).
2. SysIntro mit `AUTH_MODE=oidc` starten, jede Rolle einmal durchspielen.
3. Negativ-Tests:
   - User ohne Rollen ➜ darf einloggen, sieht aber keine Anträge.
   - Token-Ablauf mitten in Session ➜ saubere Re-Auth.
   - KC offline ➜ klare Fehlermeldung, kein Stacktrace.
4. Logout in SysIntro ➜ Keycloak-Session ebenfalls beendet.
5. Bestehende lokale Demo-User funktionieren weiter im `AUTH_MODE=local`.

### 1.6 Rollback

- `AUTH_MODE=local` zurücksetzen → bestehender lokaler Login wieder
  aktiv (sofern `password_hash` noch existiert).
- Da das `User`-Schema rückwärtskompatibel bleibt, ist kein DB-Rollback
  nötig.

---

## 2. PostgreSQL-Migration

### 2.1 Warum

- SQLite hat im Pilot perfekt funktioniert, aber kein paralleles Schreiben
  über mehrere Hosts.
- Backups, PITR, Replikation, dedizierte Monitoring-Tools sind in der
  amedes-Infrastruktur für Postgres bereits etabliert.

### 2.2 Soll-Architektur

```
   FastAPI ──── SQLAlchemy ─── (driver) ──▶ PostgreSQL 16
                                              │
                                              ├─ Hot-Standby (streaming repl.)
                                              └─ Daily pg_dump → S3-Bucket
```

### 2.3 Umsetzungsschritte

1. **Driver**: `psycopg[binary]>=3.1` zu `requirements.txt`.
2. **Konfig**: `DATABASE_URL` umstellen
   - vorher: `sqlite:////opt/sysintro/data/sysintro.db`
   - nachher: `postgresql+psycopg://sysintro:***@db.intern.amedes.de:5432/sysintro`
3. **Schema anlegen**: `alembic upgrade head` auf leerer Postgres-DB.
   Alle bestehenden Migrationen (`0001`, `0002`, `0003_poc_support`)
   sind DB-agnostisch geschrieben.
4. **Datenkopie**:
   - Empfohlen: **pgloader** mit fertigem Recipe für SQLite ➜ Postgres
     (typkonform, Auto-Inkrement-IDs werden übernommen).
   - Alternativ: kleines Python-Script über SQLAlchemy mit beiden
     Engines, das pro Tabelle `INSERT … SELECT` durchführt.
5. **Sequenz-Reset** nach Datenkopie:
   `SELECT setval(pg_get_serial_sequence('table','id'), MAX(id)) FROM table;`
   für alle PK-Tabellen.
6. **Smoke-Tests**: jede Demo-Rolle einmal einloggen, einen DRAFT
   anlegen, ein Feld editieren, einreichen, freigeben.
7. **Cutover**: SQLite-Read-Only schalten (Wartungsfenster ~30 min),
   Datenkopie wiederholen für Delta, `DATABASE_URL` umstellen,
   `systemctl restart sysintro`.

### 2.4 SQLAlchemy-Anpassungen

Aktuell sind nur drei kleine SQLite-spezifische Stellen im Code, die
gegen Postgres-Kompatibilität getestet werden müssen:

| Stelle | SQLite-spezifisch? | Postgres-Verhalten |
|---|---|---|
| `PRAGMA journal_mode=WAL` | ja | obsolet, einfach entfernen für Postgres |
| `Alembic batch_alter_table` | nur für SQLite nötig | für Postgres direkter `ALTER TABLE` möglich; bleibt aber funktional |
| `JSON`-Spalten (`enum_values`) | als TEXT | nutzt nativ `JSONB` – kein Code-Change, SQLAlchemy mappt automatisch |

### 2.5 Backup-Strategie

- **Daily**: `pg_dump --format=custom` → S3, 30 Tage Retention.
- **Continuous**: WAL-Archivierung → S3, Point-in-Time-Recovery
  möglich.
- **Restore-Test**: 1× quartalsweise auf einer separaten Maschine
  ausführen (Restore-Übung ist Pflicht für DSGVO-Aufsicht).
- **Attachments**: separates Backup für `/opt/sysintro/attachments`
  (rsync auf S3, da nicht in DB).

### 2.6 Rollback

- Vor dem Cutover wird der letzte SQLite-Stand als Snapshot abgelegt.
- Falls Postgres nicht stabil läuft: `DATABASE_URL` zurückstellen,
  `systemctl restart` – Pilot läuft weiter, bis Ursache behoben ist.

---

## 3. Mail-Versand

### 3.1 Heute

`app/services/mailer.py::would_send()` loggt nur, was versendet würde.
Keine echten E-Mails.

### 3.2 Soll

- **Option A: SMTP-Relay** der amedes-Infrastruktur (`smtp.intern.amedes.de`,
  STARTTLS, Service-Account).
- **Option B: Microsoft Graph API** (App-Registration mit
  `Mail.Send`-Rolle, OAuth2 Client-Credentials).

Empfehlung: **SMTP-Relay** für Einfachheit, falls keine
Empfänger-Personalisierung mit Branding-Templates aus Outlook nötig ist.

### 3.3 Trigger

| Ereignis | Empfänger | Inhalt |
|---|---|---|
| Antrag eingereicht | alle zuständigen Reviewer | Link zum Antrag + Felder, für die ihre Rolle zuständig ist |
| Rückfrage gestellt | Antragsteller | Feld + Rückfrage-Text + Antwort-Link |
| Antrag freigegeben | Antragsteller + App-Betrieb | Zusammenfassung |
| Antrag abgelehnt | Antragsteller | Feld + Begründung |
| Frist überfällig | Reviewer | Erinnerung |

### 3.4 Implementierung

Heutiges Stub durch `smtplib`/`emails`-Aufruf ersetzen, Templates
unter `app/templates/email/` als Jinja2 anlegen (Plain-Text + HTML).
Alle anderen Aufrufe von `mailer.would_send()` bleiben **unverändert**,
weil die Service-Schnittstelle gleich bleibt.

---

## 4. Betrieb und Backup

### 4.1 Hosting-Topologie (Soll)

```
  Cloudflare (TLS-Termination, DDoS-Schutz)
        │
        ▼
  amedes-LoadBalancer ─── nginx (Reverse-Proxy, 2 Replicas)
                              │
                              ▼
                  uvicorn / FastAPI (2 Replicas hinter LB)
                              │
                              ▼
                  PostgreSQL 16 (Primary + Hot-Standby)
                              │
                              ▼
                  S3 (Backups + Attachments)
```

Für Pilot bleibt aktuell **eine Instanz** – Skalierung sobald Last-Tests
Anhaltspunkte liefern.

### 4.2 Konfiguration (Soll-Werte für Prod)

| Variable | Pilot heute | Prod Go-Live |
|---|---|---|
| `ENVIRONMENT` | `staging` | `production` |
| `DEBUG` | `0` | `0` |
| `SECURE_COOKIES` | `1` | `1` |
| `DATABASE_URL` | sqlite:/// | postgresql+psycopg://… |
| `AUTH_MODE` | `local` | `oidc` |
| `SMTP_HOST` | – | `smtp.intern.amedes.de` |
| `LOG_LEVEL` | `INFO` | `INFO` |
| `RATE_LIMIT_LOGIN` | `5/minute` | `5/minute` |
| `SECRET_KEY` | – | aus amedes-Vault |
| `SENTRY_DSN` | – | aus amedes-Vault, optional |

### 4.3 Monitoring

- **Liveness/Readiness**: `/healthz` (existiert) und `/ready` ergänzen.
- **Metriken**: Prometheus-Endpoint `/metrics` ergänzen
  (`starlette-prometheus`).
- **Logs**: JSON-Log nach stdout → Filebeat/Loki.
- **Alerts**: 5xx-Rate > 1 %, Disk > 80 %, Cert-Ablauf < 14 Tage.

### 4.4 DSGVO / Compliance

- Audit-Log ist bereits append-only.
- Personenbezogene Daten in Anträgen werden mit dem Antrag selbst
  gelöscht (Lebenszyklus folgt amedes-Aktenplan für IT-Software-Akten).
- Auftragsverarbeitungs-Vertrag mit Cloudflare ist bereits geprüft.
- DSFA wird vor Go-Live mit dem Datenschutzbeauftragten erstellt.

---

## 5. Go-Live-Checkliste (vor Welle 1)

```
□  Keycloak-Client sysintro-web ist konfiguriert und freigegeben
□  Realm-Rollen sind angelegt und auf Test-Account zugewiesen
□  AUTH_MODE=oidc läuft eine Woche fehlerfrei auf Staging
□  PostgreSQL-Instanz ist provisioniert + Hot-Standby aktiv
□  pgloader-Lauf auf Kopie der Pilot-Daten erfolgreich getestet
□  Sequenz-Reset funktioniert, alle FK sind intakt
□  pg_dump-Restore-Test auf separater VM erfolgreich
□  SMTP-Relay erreichbar, Test-Mail versendet
□  /healthz, /ready, /metrics laufen
□  Sentry-DSN gesetzt + Test-Fehler eingeschossen
□  Pen-Test-Report ohne Critical/High
□  SBOM erzeugt + im amedes-Software-Register hinterlegt
□  DSFA fertiggestellt + vom DSB freigegeben
□  Onboarding-Slides für Reviewer-Rollen sind versandt
□  Runbook (siehe OPERATIONS.md) ist auf aktuellem Stand
□  Cutover-Wartungsfenster ist mit Service-Owner abgestimmt
```
