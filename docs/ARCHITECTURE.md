# Architektur

## Komponenten-Übersicht

```
                ┌─────────────────────────────┐
                │   Browser  (Tailwind+HTMX)  │
                └──────────────┬──────────────┘
                               │ HTTPS
                ┌──────────────▼──────────────┐
                │     nginx (reverse-proxy)   │
                └──────────────┬──────────────┘
                               │ HTTP 127.0.0.1:8080
                ┌──────────────▼──────────────────────┐
                │  uvicorn / FastAPI (app.main:app)   │
                │                                     │
                │  ┌───────────────────────────────┐  │
                │  │  app/api/   JSON-API           │  │
                │  │  app/web/   Jinja2-HTML-Routes │  │
                │  │  ┌─────────────────────────┐   │  │
                │  │  │  app/services/          │   │  │
                │  │  │   workflow              │   │  │
                │  │  │   responsibility        │   │  │
                │  │  │   category_logic        │   │  │
                │  │  │   revisions             │   │  │
                │  │  │   reminders             │   │  │
                │  │  │   audit                 │   │  │
                │  │  │   catalog               │   │  │
                │  │  │   mailer (stub)         │   │  │
                │  │  └─────────┬───────────────┘   │  │
                │  │            │ SQLAlchemy ORM    │  │
                │  └────────────┼────────────────────┘  │
                │  ┌────────────▼─────────────┐         │
                │  │  APScheduler (täglich)   │         │
                │  │  → reminders.scan()      │         │
                │  └──────────────────────────┘         │
                └──────────────┬──────────────────────┘
                               │
                ┌──────────────▼──────────────┐
                │     SQLite (WAL-Mode)       │
                │  /opt/sysintro/data/...db    │
                └─────────────────────────────┘
```

**Designprinzipien:**

1. **Routes sind dünn.** Jede Route validiert Input/Output, ruft eine Service-Funktion auf, gibt die Response zurück.
2. **Services besitzen die Schreiblogik.** Nur Service-Funktionen rufen `session.add/commit`. Routes rufen Services, fassen ORM-Objekte aber niemals direkt an.
3. **Ein Konzept pro Datei.** Jedes Modell, Schema, Service-Modul und Router-Modul deckt genau ein Domänenkonzept ab.

## Workflow-State-Machine

```
                  ┌──────────┐
                  │   DRAFT  │  ◄─ Antragsteller füllt aus, Auto-Save
                  └─────┬────┘
                        │ submit() — Pflichtfeld-Check, Kategorie-Validierung
                        ▼
                ┌──────────────┐
                │  SUBMITTED   │ — initialer Status nach Submit
                └─────┬────────┘
                      │ create ApprovalDecision pro (F-Feld × F-Rolle)
                      ▼
                ┌──────────────┐
                │ IN_REVIEW    │ ◄─────────────────────────────────┐
                └─┬────────────┘                                    │
                  │                                                  │
                  │ jede Reviewer-Entscheidung                       │
                  ├─ APPROVED  ─► alle F-Felder approved? ─► APPROVED
                  │                                                  │
                  ├─ REJECTED  ─► CHANGES_REQUESTED                   │
                  │              │                                   │
                  │              │ requester edit + resubmit          │
                  │              └──────────────────────────────────┘ │
                  │
                  │ Sonderpfad Kategorie D
                  └─► PROVISIONALLY_APPROVED  (sofortige Notfall-Freigabe)
                                  │
                                  └─► Nachgenehmigungs-Vorgang an GBR (30 Tage)
```

Final-Approval-Logik (`services/workflow.py::recompute_overall_status`):

```python
# Pseudocode
for field in approval_fields(req):
    for role in roles_that_must_approve(field):
        if not any(decision.status == APPROVED
                   for decision in decisions_for(req, field, role)):
            return  # noch nicht alle freigegeben
req.status = APPROVED
catalog.promote(req)
```

## Datenmodell (Auszug)

19 Tabellen. Wichtigste Beziehungen:

```
User ──n:m── Role
                 │
                 ├── 1:n  FieldResponsibility (kind: INFO|APPROVAL)
                 │             │
                 │             └── 1:1 FieldDefinition
                 │
                 └── 1:n  ApprovalDecision (status: IN_PROGRESS|IN_REVIEW|APPROVED|REJECTED|ACKNOWLEDGED)

ApplicationRequest
       │
       ├── 1:n FieldValue
       ├── 1:n ApprovalDecision
       ├── 1:n Comment      (threaded via parent_id)
       ├── 1:n Revision     (FIELD_CHANGE | SUBMIT_SNAPSHOT)
       ├── 1:n Attachment   (purpose: OPERATING_AGREEMENT | GENERIC)
       └── 1:1 CatalogEntry (after APPROVED)

AuditLog (append-only, no FK constraints to allow keeping history after deletes)
Reminder, Notification (separate tables)
```

Vollständiges Schema → `app/models/`.

## Field Responsibility Matrix

Jedes Feld hat pro Rolle entweder:

- **INFO (I):** Rolle sieht das Feld read-only
- **APPROVAL (F):** Rolle muss das Feld explizit freigeben

Beispiel (Auszug aus den 30 Demo-Feldern):

| Feld | BR | IT-Sec | DSB | App-Mgr | App-Op | Lic-Mgmt |
|---|---|---|---|---|---|---|
| `stammdaten.application_owner` | I | I | I | **F** | I | I |
| `produkt.hersteller` | I | I | I | **F** | I | **F** |
| `anwendung.leistungsueberwachung` | **F** | I | I | I | I | I |
| `datenschutz.personenbezogen` | I | I | **F** | I | I | I |
| `cloud.cloudbasiert` | I | **F** | **F** | I | I | I |

Vollständige Matrix in `app/seed/fields.py`.

## Reminder-Engine

```python
# scheduler.py: APScheduler täglicher Cron-Job
# services/reminders.py::scan(now)

for req in active_requests():
    for role in pending_roles(req):
        days = days_since_last_action(req, role)
        if days >= 14: send_stage_3(...)   # Admin-Eskalation
        elif days >= 7: send_stage_2(...)  # + Antragsteller
        elif days >= 3: send_stage_1(...)  # Rollen-Mitglieder

# „Schweigeperiode": Stage 1 max. 1× pro 24h
```

Demo-Hinweis: `mailer.would_send()` schreibt nur in die `notifications`-Tabelle — kein echter SMTP-Versand. Für Produktion `services/mailer.py` durch echten SMTP-Client ersetzen.

## Sicherheits-Ebenen (Defense in Depth)

| Schicht | Maßnahme |
|---|---|
| Transport | nginx + Let's-Encrypt-TLS, HSTS optional |
| Browser | HttpOnly + SameSite=Lax-Cookies, CSP via nginx (TODO produktiv), CSRF-Token |
| Anwendung | JWT-Validierung, Argon2-Passwords, Rate-Limit auf Login (5/min/IP) |
| RBAC | `require_role()`-Deps + Service-Level-Checks (`can_view`, `can_edit`) |
| Datenbank | parametrisierte ORM-Queries, append-only Audit-Log |
| OS | systemd-Hardening: `NoNewPrivileges`, `ProtectSystem=strict`, `ReadWritePaths` minimal |
| Netzwerk | ufw blockt alles außer 22/80/443 |

Details → [`docs/SECURITY.md`](SECURITY.md).

## Skalierungsgrenzen der Demo

| Aspekt | Demo-Grenze | Produktiv-Migration |
|---|---|---|
| DB | SQLite, single-writer | Postgres via Alembic-DSN-Wechsel |
| Workers | 1 uvicorn | mehrere Worker + Postgres |
| Reminder | APScheduler in-process | Celery/Redis oder externer Cron |
| Mail | Stub (in DB protokolliert) | SMTP-Relay oder Microsoft Graph |
| Auth | lokal | Keycloak via OIDC (Phase 3 lt. Spec) |
| Files | lokales Dateisystem | S3/MinIO |
