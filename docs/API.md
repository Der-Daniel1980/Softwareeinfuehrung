# API-Referenz

Alle JSON-Endpoints liegen unter `/api/v1`. Authentifizierung via JWT in HttpOnly-Cookie (`access_token`).

> **Tipp:** Beim laufenden Server sind interaktive Docs unter `/docs` (Swagger UI) und `/redoc` (ReDoc) verfügbar.

## Auth-Flow

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email": "admin@demo.local", "password": "demo1234"}
```

Antwort: `200 OK` + `Set-Cookie: access_token=<JWT>; HttpOnly; SameSite=Lax`

Folge-Requests senden den Cookie automatisch. Logout:

```http
POST /api/v1/auth/logout
```

## Rate Limiting

`/api/v1/auth/login` ist auf **5 Requests / Minute / IP** limitiert (SlowAPI). In Tests via `TESTING=1` deaktiviert.

## CSRF

State-changing API-Calls erwarten entweder `X-CSRF-Token` Header oder den HTMX-Header `HX-Request`. Browser-Frontend setzt beides automatisch.

## Endpoint-Übersicht

### Auth

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| `POST` | `/auth/login` | public | E-Mail + Passwort → Cookie |
| `POST` | `/auth/logout` | any | Cookie löschen |
| `GET` | `/auth/me` | any | aktueller User + Rollen |

### Benutzer & Stammdaten

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/users` | ADMIN | alle Benutzer |
| `POST` | `/users` | ADMIN | Benutzer anlegen |
| `GET` | `/fields` | any | Field-Definitionen + Responsibility-Matrix |
| `GET` | `/bit-fc` | any | BIT/FC-Kategorien |
| `GET` | `/system-categories` | any | A/B/C/D-Definitionen |

### Anträge

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/requests` | scoped | Liste (gefiltert nach Rolle) |
| `POST` | `/requests` | REQUESTER | neuer Draft |
| `GET` | `/requests/{id}` | scoped | Vollansicht |
| `PATCH` | `/requests/{id}` | Owner/Admin | Header-Felder ändern |
| `PATCH` | `/requests/{id}/fields/{key}` | Owner/Admin | Einzelfeld ändern (Auto-Save) |
| `POST` | `/requests/{id}/submit` | Owner/Admin | Einreichen |
| `POST` | `/requests/{id}/resubmit` | Owner/Admin | Nach Rückfrage erneut einreichen |
| `POST` | `/requests/{id}/attachments` | Owner/Admin | Datei hochladen (multipart) |
| `GET` | `/requests/{id}/attachments/{aid}` | scoped | Datei herunterladen |

### Entscheidungen, Kommentare, Revisionen

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/requests/{id}/decisions` | scoped | alle Approval-Decisions |
| `POST` | `/requests/{id}/decisions` | F-Rollen-Mitglied | Status setzen (REJECTED braucht Comment) |
| `GET` | `/requests/{id}/comments` | scoped | Kommentar-Threads |
| `POST` | `/requests/{id}/comments` | scoped | Kommentar / Reply |
| `GET` | `/requests/{id}/revisions` | scoped | Revisionsliste |
| `GET` | `/requests/{id}/revisions/{rev}` | scoped | Einzelne Revision + Snapshot |

### Applikationsverzeichnis

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/catalog` | any | Liste aller Einträge |
| `POST` | `/catalog/import` | ADMIN | Bestand importieren |
| `GET` | `/catalog/{id}` | any | Detail |
| `GET` | `/catalog/export.csv` | any | CSV-Export |

### Audit & Reminder

| Method | Path | Auth | Beschreibung |
|---|---|---|---|
| `GET` | `/audit-log` | ADMIN/AUDITOR | Audit-Log (filterbar) |
| `GET` | `/reminders` | ADMIN | gesendete Reminders |
| `POST` | `/admin/run-reminder-scan` | ADMIN | Scan manuell triggern (Demo) |

## Beispiel-Workflow per cURL

```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -c cookies.txt \
  -d '{"email":"requester@demo.local","password":"demo1234"}'

# 2. Draft erstellen
curl -X POST http://localhost:8000/api/v1/requests \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{"title":"Microsoft Project Cloud-Einführung"}'
# → {"id":1, "status":"DRAFT", ...}

# 3. Feldwert setzen
curl -X PATCH http://localhost:8000/api/v1/requests/1/fields/produkt.hersteller \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{"value":"Microsoft"}'

# 4. Einreichen
curl -X POST http://localhost:8000/api/v1/requests/1/submit \
  -H 'Content-Type: application/json' \
  -b cookies.txt \
  -d '{"category_d_confirmed_by":[]}'

# 5. Login als Reviewer + Decision setzen
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -c cookies-rev.txt \
  -d '{"email":"appmgr@demo.local","password":"demo1234"}'

curl -X POST http://localhost:8000/api/v1/requests/1/decisions \
  -H 'Content-Type: application/json' \
  -b cookies-rev.txt \
  -d '{"field_key":"produkt.hersteller","status":"APPROVED","comment":""}'
```

## Fehler-Antworten

| Status | Bedeutung |
|---|---|
| `400` | Validation Error (Pydantic) |
| `401` | Nicht authentifiziert (kein Cookie / abgelaufen) |
| `403` | Keine Berechtigung (Rolle / scope) oder CSRF |
| `404` | Resource nicht gefunden |
| `413` | Upload zu groß (> 25 MB) |
| `415` | MIME-Type nicht erlaubt |
| `422` | Geschäftsregel verletzt (z. B. REJECTED ohne Kommentar) |
| `429` | Rate-Limit überschritten (Login) |
| `500` | Interner Fehler (im Prod-Modus generische Meldung) |
