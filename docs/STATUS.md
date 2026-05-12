# SysIntro – Aktueller Stand

*Stand: 2026-05-12*

## Kurzfassung

SysIntro ist die digitale Erfassungs- und Freigabeplattform für die
Software-Einführung bei amedes. Sie ersetzt den bisher papier-/excelbasierten
Prozess, in dem Antragsteller, Betriebsrat, IT-Security, Datenschutz,
App-Manager, App-Betrieb und Lizenzmanagement parallel Felder ausfüllen,
prüfen und freigeben.

Aktueller Reifegrad: **funktionsfähiger Pilot mit kompletter Workflow-Logik,
Audit-Trail und Demo-Daten – Go-Live setzt noch Keycloak-Anbindung +
PostgreSQL-Migration voraus (Details in `GOLIVE.md`).**

---

## Was funktioniert (✅ live auf dem Pilot-Server)

### Antragsprozess

- **Antrag anlegen** – Standard *oder* POC (Proof of Concept, vereinfachter
  Workflow, später zu Standard promovierbar).
- **Dynamischer Fragenkatalog** – Felder sind nicht hartkodiert, sondern
  liegen als `FieldDefinition` in der DB. Admin kann Fragen anlegen,
  ändern, löschen und Rollen-Zuständigkeiten zuweisen (`INFO` vs
  `APPROVAL`).
- **Auto-Save** – Felder werden während des Tippens (debounced) und beim
  Verlassen automatisch gespeichert. Robust gegen Race-Condition mit
  „Einreichen"-Klick durch `flushPendingFieldEdits()`-Sweep über alle
  Input-Typen (Text, Select, Radio, Checkbox-Gruppe).
- **Bedingte Felder** – `conditional_on_key` + `conditional_equals` blendet
  abhängige Felder ein/aus (z. B. „Begründung" erscheint nur bei
  Kategorie D).
- **Systemkategorien A–D** mit eigenen Folgewirkungen (BR-Pflicht,
  BV-Anhang, Eilverfahren, vorläufige Freigabe).

### Review-Prozess

- **Pro-Feld-Entscheidungen** je Rolle: Freigegeben / Abgelehnt /
  In Prüfung. Sichtbar als Status-Chips an jedem Feld.
- **Pro-Feld-Konversation** – Rückfragen, Antworten, Kommentare
  bleiben thematisch beim Feld. Reviewer-Rückfragen aus dem
  Entscheidungs-Formular werden in den Konversations-Thread gespiegelt,
  damit der Antragsteller einen durchgehenden Gesprächsfaden sieht.
- **Reviewer-Fortschritts-Chips** mit Prioritäts-Farbcode:
  Rot = abgelehnt, Gelb = Rückfrage, Blau = teilweise erledigt,
  Grün = alles freigegeben, Grau = noch nicht gestartet.
- **Antrag zurückziehen** durch den Antragsteller, solange noch nicht
  final entschieden – bleibt im Verlauf.
- **Entwurf löschen** für DRAFT-Anträge.
- **Revisionen** – jede Feldänderung nach `SUBMITTED` wird mit altem +
  neuem Wert protokolliert; Diff-Ansicht unter `/requests/{id}/revisions`.

### Reporting

- **Dashboard** – „Meine Anträge in Prüfung", „Mit Rückfragen",
  Kachelübersicht, Reviewer-Statuschips inline.
- **Systemkatalog** – freigegebene Systeme tabellarisch + filterbar.
- **Antragsliste** – pro-Antrag-Fortschritt mit Pro-Rolle-Chips inline.
- **Audit-Log** – append-only, sichtbar pro Antrag und global.

### Admin

- **Fragenkatalog-Verwaltung** (`/admin/fields`) – CRUD über
  `FieldDefinition` + `FieldResponsibility`. Inkl. POC-Flag pro Feld,
  bedingte Felder, Enum-Werte, Pflicht-Markierung.
- **Stammdaten** – Rollen, Benutzer, Systemkategorien, BIT/FC,
  Vendoren.

### Sicherheit (bereits umgesetzt)

- Argon2 für Passwörter, JWT in HttpOnly + SameSite=Lax Cookie.
- CSRF-Double-Submit auf allen non-GET Web-Routes.
- Rate-Limit auf `/auth/login`.
- File-Upload: 25 MB Maximum, MIME-Whitelist, UUID-Filenames.
- Audit-Log append-only.
- Cloudflare-TLS-Termination + nginx-Reverse-Proxy.

---

## Was offen ist (🟡 für Go-Live nötig)

| Thema | Status | Details |
|---|---|---|
| **Keycloak-SSO** | 🔴 offen | Architektur entworfen – siehe `GOLIVE.md`. Heute: lokale Argon2-User. |
| **PostgreSQL** | 🔴 offen | Heute: SQLite. Migration via Alembic + Datenkopie via pgloader vorgesehen. |
| **Mail-Versand** | 🟡 stub | `mailer.would_send` loggt nur. Anbindung an amedes-SMTP / Microsoft Graph noch zu konfigurieren. |
| **Backup / Restore** | 🟡 manuell | sqlite3-Dump per Cron auf dem Pilot. Für Postgres → `pg_dump`-Plan in `GOLIVE.md`. |
| **Härtung** | 🟢 grundsätzlich | Container-Scan, Pen-Test, SBOM-Generierung vor Go-Live. |
| **Branding** | 🟡 offen | „SysIntro" ist Arbeitstitel. Endgültiger Name + Logo durch amedes-Kommunikation. |

---

## Demo-Zugänge (Pilot)

| Rolle | E-Mail | Test-User |
|---|---|---|
| Antragsteller | max@example.com | Max Mustermann |
| Betriebsrat | britta@example.com | Britta BR |
| IT-Security | ina@example.com | Ina IT-Security |
| Datenschutz | dora@example.com | Dora DSB |
| App-Manager | anton@example.com | Anton AppMgr |
| App-Betrieb | otto@example.com | Otto Ops |
| Lizenzen | lisa@example.com | Lisa Lic |
| Admin | admin@example.com | Admin |

Passwörter: siehe interne Notiz (nicht in Git).

Demo-Anträge im Pilot enthalten u. a.: SAP S/4HANA, t2med, copa.ris,
Dynamics 365 CRM, ChatGPT Enterprise, Microsoft 365 Copilot – mit
Mischung aus DRAFT, SUBMITTED, IN_REVIEW, APPROVED.

---

## Roadmap (grober Plan)

1. **Q2 2026 – Pilot-Härtung**
   - Keycloak-Integration (`AUTH_MODE=oidc`)
   - PostgreSQL-Migration
   - SMTP-Anbindung
   - Pen-Test + Härtung

2. **Q3 2026 – Go-Live Welle 1**
   - Antragsteller aus IT + Fachbereich
   - Vollständiger Workflow live
   - Onboarding-Sessions für Reviewer-Rollen

3. **Q4 2026 – Welle 2 + Auswertung**
   - Reporting-Erweiterung (Auswertung Bearbeitungszeiten,
     Engpass-Erkennung)
   - Optional: Entra ID / Active Directory Synchronisation
   - Optional: Workflow-Templates für wiederkehrende Software-Typen
