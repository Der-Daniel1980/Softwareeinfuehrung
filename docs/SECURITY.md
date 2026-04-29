# Sicherheits-Konzept

## Schutzziele

| Ziel | Maßnahme | Ort |
|---|---|---|
| **Vertraulichkeit** | TLS, HttpOnly-Cookies, Rate-Limit | nginx, app |
| **Integrität** | Append-only Audit-Log, Revisionen, parametrisierte Queries | `services/audit.py`, ORM |
| **Verfügbarkeit** | systemd-Restart, ufw-Firewall | systemd-Unit |
| **Nachvollziehbarkeit** | Audit-Log, Revisionen pro Feld | `services/revisions.py` |
| **Compliance (DSGVO)** | personenbezogene Daten minimal in Logs, Pseudonymisierung möglich | `services/audit.py` |

## Authentifizierung

- **Argon2** (`argon2-cffi`, default Parameter; in `core/security.py`)
- **JWT** mit HS256, Secret aus `SECRET_KEY`-Env (in `install.sh` zufällig generiert: `openssl rand -hex 32`)
- **Cookie-Flags:** `HttpOnly`, `SameSite=Lax`, `Secure` wenn `SECURE_COOKIES=1` (gesetzt durch `install.sh --tls`)
- **Token-TTL:** 480 Minuten (8h) per Default; konfigurierbar via `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Phase-2-Vorgesehen (Spec):** Keycloak via OIDC, MFA für Admin/Approver

## Autorisierung

- **RBAC** auf Routen-Ebene via FastAPI-Deps (`require_role`, `require_admin`, `require_admin_or_auditor`)
- **Service-Level-Checks** zusätzlich (`workflow.can_view`, `workflow.can_edit`) — keine Verlässlichkeit auf UI-Visibility
- **Field-Level:** Reviewer kann nur Decisions für Felder setzen, die seine Rolle als `APPROVAL` markiert hat (Check in `services/workflow.py::set_decision`)
- **Request-Scoping:** REQUESTER sieht nur eigene Anträge; AUDITOR/ADMIN sehen alles; Approver sehen Anträge ab `SUBMITTED`, bei denen ihre Rolle Verantwortung hat

## Eingabe-Validierung

- **Pydantic v2** auf allen API-Schemas
- **Form-Inputs** der Web-Routes ebenfalls über FastAPI's `Form()`
- **Pflichtfeld-Validierung** vor Submit (in `services/category_logic.validate_for_submit`)

## SQL-Injection

- Ausschließlich SQLAlchemy ORM, keine Raw-Queries
- Verifiziert: `grep -r "execute.*f\""` und `grep -r "execute.*%s"` → keine Treffer

## XSS

- Jinja2 Auto-Escape ist standardmäßig aktiv
- Einzige `|safe`-Stellen wären explizit markiert (aktuell: keine)
- Inline-`<script>` nur für statische CDN-Loader und nicht-userinput-bezogene Helper

## CSRF

- **SameSite=Lax-Cookies** als primäre Verteidigung — Browser senden bei Cross-Site-POST keine Cookies mit
- **Double-Submit-Token** (`csrf_token`-Cookie + `X-CSRF-Token`-Header) zusätzlich verfügbar (`core/csrf.py`)
- **HTMX-Header-Check:** `verify_api_csrf` akzeptiert bei Requests mit `HX-Request`-Header (Browser können diesen Header nicht cross-origin ohne CORS-Preflight setzen, der wiederum durch unsere `CORSMiddleware` auf konkrete Origins limitiert ist)

## CORS

`app/main.py`:

```python
allow_origins=settings.CORS_ORIGINS.split(",")     # genau die konfigurierten Origins
allow_credentials=True
allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"]
allow_headers=["Content-Type","Authorization","X-CSRF-Token","HX-Request","HX-Target","HX-Trigger"]
```

Kein Wildcard. Nur Origins aus `CORS_ORIGINS`-Env (in Prod = die eigene Domain).

## File Uploads

`app/api/requests.py::upload_attachment`:

- **MIME-Whitelist:** PDF, PNG, JPEG, DOCX, DOC, TXT, XLS, XLSX (in `config.py::ALLOWED_MIME_TYPES`)
- **Max-Größe:** 25 MB (`MAX_UPLOAD_BYTES`); auch nginx setzt `client_max_body_size 25m`
- **Speicher-Pfad:** `<UPLOAD_DIR>/<request_id>/<uuid>.<extension>` — kein User-Input im Pfad, daher path-traversal-sicher
- **Original-Filename** nur in DB persistiert, nicht im Filesystem
- **Download-Route** prüft `request_id == attachment.request_id` und ruft `workflow.can_view(req, user)` auf

## Audit-Log

- Tabelle `audit_logs` ist **append-only auf App-Ebene** — der Service `services/audit.py` exponiert nur `log()`, kein `update()` oder `delete()`
- **Datenbank-Garantie auf SQL-Ebene** ist nicht erzwungen (SQLite/Postgres haben keine Trigger im Demo) — würde produktiv durch DB-Trigger oder separate Append-only-DB ergänzt
- **Logged Actions:** LOGIN, LOGOUT, FIELD_UPDATED, STATUS_CHANGED, DECISION_SET, COMMENT_ADDED, REMINDER_SENT, CATEGORY_CHANGED, REQUEST_SUBMITTED, REQUEST_APPROVED, REQUEST_REJECTED, USER_CREATED, ATTACHMENT_UPLOADED

## Secrets

- **`SECRET_KEY`** wird beim ersten Lauf von `install.sh` via `openssl rand -hex 32` erzeugt und in `/opt/sysintro/.env` mit Mode 600 abgelegt
- `.env` ist in `.gitignore`
- `.env.example` enthält nur Platzhalter (`CHANGE_ME_*`)
- Idempotenz: bei Re-Run von `install.sh` wird existierende `.env` NICHT überschrieben

## OS-Härtung (systemd)

`deploy/sysintro.service`:

```ini
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=/opt/sysintro/data /opt/sysintro/attachments /opt/sysintro/logs
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
RestrictRealtime=true
LockPersonality=true
```

## Netzwerk

- nginx als einziger Public-facing Service
- App lauscht ausschließlich auf `127.0.0.1:8080`
- ufw: nur 22 (SSH), 80, 443 offen

## Härtungs-Checkliste vor Produktiv-Go-Live

- [ ] **SSH-Key-Auth** statt Passwort, Passwort-Login deaktivieren
- [ ] **fail2ban** für SSH und nginx
- [ ] **Demo-Benutzer entfernen** (alle `*@demo.local`)
- [ ] **Admin-Passwort** wechseln, MFA aktivieren (Phase 2)
- [ ] **Backup-Job** für SQLite-DB (täglich, off-host)
- [ ] **Log-Forwarding** (z. B. an ELK/Loki)
- [ ] **TLS** mit `--tls` einrichten und HSTS in nginx aktivieren (im Skript auskommentiert)
- [ ] **Content-Security-Policy** in nginx setzen (aktuell nicht gesetzt, da Tailwind/HTMX von CDN — produktiv: lokal hosten)
- [ ] **DSGVO-Verarbeitungsverzeichnis** anlegen
- [ ] **Penetrationstest** durchführen (Spec Phase 4)

## Bewusste Design-Entscheidung: Vollständige Request-Sicht für Reviewer

**Verhalten:** Sobald ein Reviewer (Rolle BR / IT-Sec / DSB / App-Mgr / App-Op / Lic-Mgmt) **irgendeine** Verantwortung (I oder F) auf einem Antrag hat, sieht diese Person den **vollständigen** Antrag inklusive aller Felder — auch derer, für die seine Rolle weder INFO noch APPROVAL gesetzt ist.

**Begründung:** Das spiegelt die Excel-Vorlage, in der jeder Freigeber das Gesamtformular zur Kontextprüfung sah. Eine isolierte Sicht nur auf eigene Felder würde sinnvolle Freigaben erschweren (z. B. kann der Lizenzmanager den Lizenzbedarf nur einschätzen, wenn er auch Standorte und Mitarbeiterzahl sieht).

**Implikation:** Wenn ein Antrag wirklich sensitive Daten enthält (z. B. Krankenakten-Schemas in Frage 6.x), sollten Antragsteller nur das technisch nötige Minimum eintragen. Vertrauliche Anhänge sollten **nicht** über das Anhang-Upload, sondern separat abgelegt werden (Verweis im Feld auf eine externe ACL-geschützte Quelle).

**Migration zu Field-Level-ACL:** falls erforderlich, in `app/api/requests.py::_to_read()` `field_values` pro Viewer-Rolle filtern (`responsibility.fields_visible_to(role) → set[str]`). Dies bricht den aktuellen Workflow nicht, beschränkt aber die Sicht.

## Bekannte Demo-Limitierungen

| Limitierung | Auswirkung | Migration-Pfad |
|---|---|---|
| Tailwind/HTMX via CDN | externe Abhängigkeit, keine echte CSP möglich | lokal hosten + CSP setzen |
| Kein echter SMTP-Versand | Reminder-Mails nur in DB | `services/mailer.py` durch SMTP-Client ersetzen |
| Single-User-Edit ohne Lock | letzte Speicherung gewinnt | optimistic locking via `updated_at`-Vergleich |
| Kein PDF-Export | nur CSV des Verzeichnisses | WeasyPrint oder ReportLab integrieren |
| Kein OIDC | lokale Auth | Keycloak via `python-jose-cryptography` + Discovery |
