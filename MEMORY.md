# SysIntro – Session-Memory

Dieses Dokument fasst den aktuellen Stand zusammen, damit wir in einer
neuen Session sofort weitermachen können, ohne Kontext zu verlieren.
Aktualisiere es am Ende jeder Sitzung mit dem, was sich geändert hat
und was als Nächstes ansteht.

---

## 1. Worum geht es überhaupt

**SysIntro** ist eine **interne Demo-Web-App für amedes**, die den Workflow
„Software-/System­einführung" digital abbildet. Antragsteller füllen einen
Fragebogen aus, mehrere Reviewer-Rollen (Betriebsrat, IT-Sicherheit, Daten­schutz,
App-Manager, App-Operation, Lizenz­management) prüfen ihre jeweiligen Felder
und geben frei oder lehnen ab. Genehmigte Anträge wandern in den **System­katalog**.

Der Name „SysIntro" ist nur Arbeits­titel/Code-Name — wenn der Kunde einen
Brand-Namen wünscht, müssen Templates `base.html`, `nav.html`, `login.html`
und `base.html`-Title geändert werden (Ordner `/opt/sysintro/`, systemd-Unit
und DB-Datei bleiben unverändert).

---

## 2. Tech-Stack

- **Python 3.13** (auf dem Server) / 3.11+ als Mindest­anforderung
- **FastAPI** + **SQLAlchemy 2.x** + **Alembic**
- **Jinja2** + **Tailwind** (CDN) + **HTMX** für interaktive Formulare
- **SQLite** mit WAL-Modus (`/opt/sysintro/data/sysintro.db`)
- **uvicorn** Single-Worker hinter **nginx** (Reverse-Proxy + TLS)
- **APScheduler** für Reminder-Scan (07:00 daily)
- **Argon2** für Passwörter, JWT in HttpOnly-Cookie, CSRF Double-Submit
- **`uv`** als Paket-Manager lokal (auf dem Server: klassisches `venv` unter
  `/opt/sysintro/venv/`)

Coding-Konventionen siehe `CLAUDE.md` (Routes thin, Services own writes,
1 Konzept pro Datei, Pydantic v2, ruff clean).

---

## 3. Server-Zugang

| Zweck | Wert |
|---|---|
| Server-IP (primär) | `138.199.213.218` (oft Connection-Timeout) |
| Server-IP (fallback) | `187.124.2.31` (bisher zuverlässig) |
| User | `root` |
| App-Pfad | `/opt/sysintro/` |
| Projekt-Wurzel mit Code | `/opt/sysintro/app/` (enthält `app/`, `alembic/`, …) |
| Python-Package | `/opt/sysintro/app/app/` |
| systemd-Unit | `sysintro.service` |
| uvicorn-Port (intern) | `127.0.0.1:8080` |
| Web-Frontend | hinter nginx auf Port 443 (TLS) |
| Statische Datei | `/opt/sysintro/app/app/static/` |
| DB | `/opt/sysintro/data/sysintro.db` |
| Backups (manuell) | `/opt/sysintro/data/sysintro.db.bak.<epoch>` |
| Service-User | `sysintro:sysintro` |
| Passwort | im Chat geteilt (NICHT hier hartcoden) |

**Deploy-Pattern in Git-Bash unter Windows** (kein sshpass, plink etc.):

```bash
# einmalig pro Session:
cat > /tmp/askpass.sh <<'EOF'
#!/bin/sh
echo '<PASSWORT>'
EOF
chmod +x /tmp/askpass.sh

# scp + ssh-Aufrufe:
SSH_ASKPASS=/tmp/askpass.sh SSH_ASKPASS_REQUIRE=force DISPLAY=fake \
  scp -o StrictHostKeyChecking=no -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no <local> root@<ip>:<remote>

SSH_ASKPASS=/tmp/askpass.sh SSH_ASKPASS_REQUIRE=force DISPLAY=fake \
  ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no root@<ip> '<cmd>'
```

Nach jedem Code-Update auf dem Server:

```bash
chown -R sysintro:sysintro /opt/sysintro/app
systemctl restart sysintro && sleep 2 && systemctl is-active sysintro
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/login   # 200 erwartet
```

Bei Migrations:

```bash
cd /opt/sysintro/app && /opt/sysintro/venv/bin/alembic upgrade head
```

---

## 4. Demo-User (`demo1234` für alle)

| E-Mail | Rolle | Bemerkung |
|---|---|---|
| `admin@demo.local` | ADMIN | nur ADMIN, kein REQUESTER |
| `requester@demo.local` | REQUESTER | „Max Mustermann" – Standard-Tester |
| `owner@demo.local` | REQUESTER | „Olivia Owner" – Application Owner in Demos |
| `br@demo.local` | BETRIEBSRAT | „Britta BR" |
| `itsec@demo.local` | IT_SECURITY | „Ingo IT-Sec" |
| `dsb@demo.local` | DATA_PROTECTION | „Diana DSB" |
| `appmgr@demo.local` | APP_MANAGER | „Anna App-Mgr" |
| `appop@demo.local` | APP_OPERATION | „Otto App-Op" |
| `lic@demo.local` | LICENSE_MGMT | „Lars Lizenz" |
| `auditor@demo.local` | AUDITOR | nur Lese­rechte + Audit-Log |

User-IDs sind in der Reihenfolge 1–10 vergeben (deterministisch durch Seed).

---

## 5. Datenmodell auf einen Blick

- **`application_requests`** — der Antrag selbst (Title, Status, system_category,
  application_owner_id, it_application_owner_id, short_description,
  installation_location, **`is_poc` BOOL**, **`promoted_from_poc_id` INT?**)
- **`field_definitions`** — Fragenkatalog (key `bereich.feld`, label, input_type,
  enum_values, is_required, conditional_on_key/equals, sort_order,
  **`included_in_poc` BOOL**)
- **`field_responsibilities`** — pro Feld×Rolle: `kind ∈ {INFO, APPROVAL}`
- **`field_values`** — die Antworten (`request_id`, `field_key`, `value_text`)
- **`approval_decisions`** — Reviewer-Entscheidungen pro (Antrag×Feld×Rolle)
  mit `status ∈ {IN_PROGRESS, IN_REVIEW, APPROVED, REJECTED, ACKNOWLEDGED}`
- **`comments`** — Threaded Q&A (`parent_id`, `field_key`, `role_id`)
- **`revisions`** — Versions­historie (FIELD_CHANGE mit alt/neu, SUBMIT_SNAPSHOT
  mit JSON-Snapshot)
- **`catalog_entries`** — System­katalog (FROM_REQUEST × IMPORTED)
- **`audit_logs`** — append-only

**Antrags-Status­workflow**:
`DRAFT → SUBMITTED → IN_REVIEW → CHANGES_REQUESTED → IN_REVIEW → APPROVED`
(plus `REJECTED`, `WITHDRAWN`, `PROVISIONALLY_APPROVED` für Kategorie D).

---

## 6. Was schon funktioniert (Stand: Session 7. Mai 2026)

### Antragsteller-Flow
- Antrag anlegen mit Wahl **Standard-Antrag** oder **🧪 Proof of Concept (POC)**
- Auto-Save während Tippen (`hx-trigger="input changed delay:800ms, blur, change"`)
- Manueller **💾 Speichern**-Button am Footer
- **✓ Einreichen**-Button oben **und** unten (synchron disabled bis alle
  Pflichtfelder befüllt)
- `flushPendingFieldEdits()` schickt vor Submit ALLE sichtbaren Werte
  synchron zum Server (TEXT, NUMBER, DATE, TEXTAREA, SELECT, RADIO,
  CHECKBOX-Gruppen) → keine Race-Conditions mehr
- Felder bleiben nach Submit weiter bearbeitbar (SUBMITTED/IN_REVIEW), jede
  Änderung in `revisions` mit Diff
- Verlauf-Seite mit Vorher/Nachher-Diff
- Antrag **zurückziehen** (→ WITHDRAWN, mit optionalem Begründungs-Snapshot)
- DRAFT **löschen** (Button im Header **und** in der Liste)
- POC → Standard **promovieren** (`/api/v1/requests/{id}/promote_to_standard`)
  – legt neuen DRAFT mit kopierten Feld­werten + BIT/FC-Verknüpfungen an

### Reviewer-Flow
- Per-Feld Approve/Reject + Kommentar
- Threaded Q&A pro Feld (Reviewer fragt, Antragsteller antwortet)
- Reviewer-Status-Chips überall (Dashboard, Liste, Edit, Review):
  - 🔴 Rot = Ablehnung
  - 🟡 Gelb = offene Rückfrage
  - 🟢 Grün = alles freigegeben
  - 🔵 Blau = teilweise freigegeben / in Bearbeitung
  - ⚪ Grau = noch nichts gemacht
- Sidebar-Counter berücksichtigt Conditional-Felder (überspringt sie, wenn
  Trigger nicht aktiv ist)

### Admin
- **`/admin/users`** – User-Verwaltung
- **`/admin/vendors`** – Hersteller-Stammdaten
- **`/admin/audit`** – Audit-Log
- **`/admin/fields`** – **Fragenkatalog komplett editierbar**:
  - neue Fragen anlegen / bestehende ändern / löschen (nur wenn nirgends
    befüllt)
  - Pro Frage: Pflicht, ENUM-Werte (JSON), bedingte Sicht­barkeit,
    POC-Markierung, Reihen­folge
  - Pro Rolle: 3-Wege-Radio **keine / Info / Freigabe**

### Server-Mirror für strukturelle Felder
`patch_field` spiegelt automatisch in `application_requests`-Spalten:
- `system_category.code` → `system_category`
- `stammdaten.short_description` → `short_description`
- `stammdaten.installation_location` → `installation_location`
- `stammdaten.application_owner` → `application_owner_id` (Lookup nach
  Name oder E-Mail)
- `stammdaten.it_application_owner` → `it_application_owner_id`

`category_logic.validate_for_submit` hat zusätzlich Self-Heal: wenn die
`system_category`-Spalte leer ist, aber `field_values.system_category.code`
einen gültigen Wert hat, wird er beim Submit-Versuch in die Spalte gespiegelt.

### Cache-Bust
`templates.py` setzt `static_version` (mtime der jüngsten static-Datei) als
Jinja-Global, `base.html` und `login.html` hängen `?v={{ static_version }}`
an `/static/app.js` und `/static/app.css`. nginx `max-age=86400` ist damit
unproblematisch — bei jedem Code-Deploy bekommt der Browser sofort die
neue Datei. Token bumpt sich automatisch durch `touch`.

### Demo-Daten (10 Anträge)
- **Keycloak** SUBMITTED B
- **Kubernetes** IN_REVIEW B
- **Claude Code** DRAFT
- **Power BI Pro** DRAFT A
- **SAP S/4HANA Finance** IN_REVIEW C
- **copa.ris** SUBMITTED C (1:1 aus der amedes-Excel)
- **t2med** ✅ APPROVED A (komplett grün)
- **Microsoft Dynamics 365 CRM** ✅ APPROVED B (komplett grün)
- **ChatGPT Enterprise** IN_REVIEW B (3 offene Rückfragen)
- **M365 Copilot** SUBMITTED B

Plus **15 System­katalog-Einträge** (2 aus genehmigten Anträgen, 13 als
historische IMPORTED-Einträge: M365, SAP HCM, Citrix, VMware, Veeam, IGEL,
Atlassian, GitLab, PRTG, KeePassXC, Roche cobas, Sysmex, Beckman DxH).

---

## 7. Bekannte Stolpersteine

- **Browser-Cache** war die Wurzel mehrerer Phantom-Bugs. Nach jedem Deploy
  bumpt der Cache-Bust automatisch — User braucht trotzdem manchmal
  **Strg+Shift+R**, weil Service-Worker / Browser-Heuristiken zickig sind.
- **Cloudflare** liegt davor (siehe Logs `172.69.…` als Source-IP). Falls
  ein API-Call mysteriös 502/520 liefert: dort prüfen.
- **`promoted_from_poc_id`** ist ein Self-FK auf `application_requests.id`,
  Migration 0003 setzt einen expliziten Constraint-Namen (`fk_application_…`),
  weil Alembic-Batch-Mode auf SQLite sonst meckert.
- **Login-Template `login.html` extends NICHT `base.html`** — eigene
  `<head>`-Sektion. Beim Anpassen von Globals (z. B. Cache-Bust) auch hier
  anfassen.
- Status-Codes für Browser: `RequestStatus.WITHDRAWN` ist erst seit
  Session 30. April im Enum; alle Status-Badges/-Filter berücksichtigen ihn.
- **`/admin/fields/{id}/delete`** verlangt, dass das Feld noch nirgends
  befüllt ist — sonst 409. Stattdessen Pflicht entfernen / Feld umbenennen.

---

## 8. Was als Nächstes ansteht

### 🎯 Hauptziel (Mittelfrist): **Keycloak-Integration**

Aktuell hat die App eine eigene User-Tabelle mit Argon2-Passwörtern. Ziel ist
ein produktiver Single-Sign-On gegen Keycloak (intern bei amedes ohnehin als
zentrale IAM-Plattform geplant, siehe Demo-Antrag #1).

**Vorbereitende Überlegungen** (noch nicht umgesetzt, mit dem User abstimmen):

1. **Auth-Modus konfigurierbar**: ENV `AUTH_MODE = local | oidc`. Im OIDC-Modus
   wird Login gegen Keycloak (Auth-Code-Flow + PKCE) gemacht; lokale
   User-Tabelle fungiert nur noch als Profil-Cache + Rollen­zuordnung.
2. **Rollen-Mapping**: Keycloak-Realm-Rollen → unsere `roles.code`. Beim ersten
   Login wird der User automatisch (Just-in-Time) angelegt; Rollen aus dem
   ID-Token werden synchronisiert.
3. **Logout** muss über Keycloak's End-Session-Endpoint laufen, sonst bleibt
   die KC-Session aktiv.
4. **CSRF/JWT-Cookie** unverändert lassen; nach erfolgreichem OIDC-Callback
   stellen wir unser eigenes Session-Cookie aus, damit der bestehende Code
   nichts merkt.
5. **Demo-Modus** beibehalten: ENV-Schalter `DEMO_LOCAL_LOGIN=1` für
   Workshop-Demos ohne KC.

**Bibliotheken**: `authlib` (gut dokumentiert, async-fähig, OIDC-Discovery,
PKCE built-in). Alternativ direkter HTTPX + `python-jose` für JWT-Validierung.

**Nicht starten, bis User explizit grünes Licht gibt** — momentan steht
explizit „erstmal so weiter".

### 🔧 Aufgaben für die nächsten Sessions (User-Wünsche aus dem Chat-Verlauf)

Diese Liste ist nicht erschöpfend — wir arbeiten ad-hoc, was der User
priorisiert. Aktueller Stand:

- ✅ **Erledigt** in der letzten Session: Footer-Aktions­leiste mit
  Speichern + Einreichen, Race-Condition Submit↔Patch behoben (alle
  Feldtypen im Flush), Fehler­meldungen scrollen automatisch zur Sicht­barkeit.

- 🔭 **Noch offen / wahrscheinlich**:
  - „SysIntro" durch echten Brand-Namen ersetzen (User noch unentschieden)
  - eventuell weitere Reviewer-Rollen / Workflow-Anpassungen
  - eventuell Mail-Versand realisieren (aktuell `mailer.would_send` nur
    Logging)
  - Datei-Anhänge UI feinschleifen
  - **Keycloak** (s. o.)

### 🧪 Technical Debt / Aufräumen

- `print()` aus den `seed_*.py`-Skripten ist OK (CLI), Rest sollte `logging`
  benutzen — bisher konsequent gemacht.
- Tests in `tests/` sind nicht alle aktuell — bei größeren Refactors checken.
- `ruff check .` sollte clean sein vor jedem Commit (siehe CLAUDE.md).
- Alembic-Migrations 0001 / 0002 / 0003 — bei nächster Schema-Änderung
  Nummer 0004 verwenden.

---

## 9. So startet eine neue Session schnell

1. Lies dieses File
2. Schau in `CLAUDE.md` für Code-Konventionen
3. Spec ist in `SPEC.md`
4. Schau in `git log --oneline -20` für die letzten Commits
5. Auf dem Server kurz ssh’en und `systemctl is-active sysintro` +
   `journalctl -u sysintro -n 30 --no-pager` checken — Status ist die
   beste Wahrheit
6. Lokaler Stand vs. Server: Code wird ohne Git auf den Server geschoben
   (per `scp` ins jeweilige Verzeichnis), nicht per `git pull` — der Server
   ist also kein Git-Repo. Wenn etwas live wirken soll, muss es geSCPt und
   die Datei-Owner auf `sysintro:sysintro` korrigiert werden.

---

_Letzte Aktualisierung: 7. Mai 2026 (Session-Ende: Footer-Aktions­leiste +
Race-Condition-Fix Submit↔Patch deployed)._
