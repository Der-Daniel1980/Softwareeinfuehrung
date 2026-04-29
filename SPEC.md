# Konzept: Webanwendung "Systemeinführung & Applikationsverzeichnis"

**Arbeitstitel:** SysIntro (Platzhalter, anpassbar)
**Auftraggeber:** amedes-Gruppe, IT Application Management
**Stand:** 28.04.2026
**Zweck dieses Dokuments:** Konzept-/Spezifikationsgrundlage für die Umsetzung mit Claude Code. Dieses Dokument soll als `SPEC.md` bzw. `CLAUDE.md` im Projekt-Repository abgelegt werden.

---

## 1. Zielsetzung

Die Webanwendung ersetzt den bisherigen Excel-basierten Prozess zur Systemeinführung und -änderung (Frageliste). Sie

- digitalisiert den Antragsprozess inklusive aller bisher in Excel geforderten Angaben,
- steuert die Freigaben durch sechs Fachbereiche (Betriebsrat, IT Sicherheit, Datenschutz, Application Manager, Application Operation, Lizenzmanagement),
- hält jede Änderung revisionssicher fest,
- baut im Hintergrund ein zentrales **Applikationsverzeichnis** auf,
- erinnert automatisch an offene Freigaben,
- ist später mit Keycloak (SSO) integrierbar.

## 2. Glossar

| Begriff | Bedeutung |
|---|---|
| **Antrag (Application Request)** | Konkrete Anforderung zur Einführung oder Änderung eines Systems |
| **Antragsteller (Requester)** | Mitarbeitende:r, der/die den Antrag erstellt |
| **Freigeber (Approver)** | Person aus einer der sechs freigebenden Rollen |
| **Feld (Field)** | Einzelne Zeile/Frage im Fragenkatalog (z. B. "Hersteller", "Rechtsgrundlage") |
| **Feldstatus** | Status pro Feld pro Rolle (z. B. *Freigegeben*) |
| **Antragsstatus** | Übergeordneter Status des gesamten Antrags |
| **Applikationsverzeichnis** | Read-/Edit-Ansicht aller produktiv genutzten Systeme |
| **Revision** | Versionierter Snapshot eines Antrags (jede Änderung wird gespeichert) |

## 3. Rollen und Berechtigungen

### 3.1 Rollenmodell

| Rolle | Aufgabe | Mehrfachzuweisung möglich? |
|---|---|---|
| Antragsteller | Antrag stellen, Felder ausfüllen, auf Kommentare reagieren | Ja (jede:r Mitarbeitende:r) |
| Betriebsrat | Freigabe & Kommentierung der ihn betreffenden Felder (BR-relevante Felder, vgl. Spalte I der Excel) | Ja, mehrere Personen |
| IT Sicherheitsbeauftragter | Freigabe & Kommentierung sicherheitsrelevanter Felder | Ja |
| Datenschutzbeauftragter | Freigabe & Kommentierung datenschutzrelevanter Felder | Ja |
| Application Manager | Freigabe & Kommentierung fachlicher Felder | Ja |
| Application Operation | Freigabe & Kommentierung betrieblicher Felder | Ja |
| Lizenzmanagement | Freigabe & Kommentierung lizenz-/kostenrelevanter Felder | Ja |
| Administrator | Stammdaten, Rollen, Reminder-Konfiguration, Templates verwalten | Klein |
| Auditor (read-only) | Reine Einsicht für Audits/Compliance | Klein |

### 3.2 Rollenverwaltung (Phase 1: manuell)

- Admin pflegt Benutzer und ordnet sie einer oder mehreren Rollen zu.
- Pro Rolle können beliebig viele Personen zugeordnet werden – jede dieser Personen kann freigeben (logische ODER-Verknüpfung pro Rolle, d. h. **eine** Freigabe pro Rolle reicht; konfigurierbar als „Mindestens 1 von n").
- Jede Rolle besitzt eine **Verteilerliste** (E-Mail), an die Benachrichtigungen gehen, falls keine Person aktiv ist.

### 3.3 Spätere Keycloak-Integration

- Authentifizierung via OIDC, Rollen werden aus Keycloak-Gruppen gemappt.
- User-Provisionierung: Just-in-Time bei erstem Login, Stammdatenabgleich aus AD via Keycloak-Föderation.
- Vorgesehen: Konfigurierbares Mapping `keycloakGroup → AppRole`.

## 4. Spalten-Semantik aus der Excel-Vorlage (I = Information, F = Freigabe)

Die Spalten I–N der Frageliste enthalten pro Rolle entweder `I` oder `F`:

- **I (Information):** Die Rolle muss das Feld nur **einsehen** – keine eigene Freigabe nötig.
- **F (Freigabe):** Die Rolle muss das Feld **explizit freigeben** (Status auf "Freigegeben" setzen).

Diese Matrix wird als **Field Responsibility Matrix** in die Datenbank übernommen. Die Anwendung leitet daraus pro Rolle automatisch ab, welche Felder sie freigeben muss.

## 4a. Ergänzende Stammdaten und Systemkategorisierung

> **Kontext:** Aus dem bestehenden amedes-Bestellprozess („In den Warenkorb für Einführung neue Software/SaaS") sind weitere Stammdaten und insbesondere eine **Systemkategorie A–D** zur Mitbestimmungsbewertung durch den Betriebsrat zu übernehmen. Diese Felder ergänzen die bisherige Excel-Frageliste und sind in der App zu integrieren.

### 4a.1 Erweiterte Stammdaten zur Anwendung

Zusätzlich zu den Feldern der bisherigen Frageliste werden folgende Stammdaten am Antrag erfasst:

| Feld | Pflicht | Eingabe | Erläuterung |
|---|---|---|---|
| **Application Owner** (fachlich) | ja | Personenauswahl (1) | Fachlich verantwortliche Person für die Anwendung. Trifft fachliche Entscheidungen, Ansprechpartner für Anforderungen. |
| **Application Owner Stellvertreter** | ja | Personenauswahl (1+) | Vertretungsregelung des fachlichen Owners. |
| **IT Application Owner** (technisch) | ja | Personenauswahl (1) | Technisch verantwortliche Person aus der IT. Ansprechpartner für Betrieb, Schnittstellen, technische Änderungen. |
| **IT Application Owner Stellvertreter** | empfohlen | Personenauswahl (1+) | Vertretung des technischen Owners. |
| **Betroffene BIT-/FC-Kategorie** | ja | Auswahl aus Stammdaten | Zuordnung zur Business-IT- bzw. Fachbereichs-Kategorie der amedes-Organisation (Multi-Select möglich, falls bereichsübergreifend). |
| **Beschreibung** | optional | Freitext (kurz) | Kurzbeschreibung der Anwendung als Tagline – ergänzend zur ausführlichen Systembeschreibung (Frage 2.3). |
| **Wo wird die Software installiert** | ja | Freitext / Auswahl | Installationsort: amedes-RZ, Cloud-Region, Endgerät, etc. (separat zur „auszurollenden Standorte"-Frage 3.2 – diese betrifft die Nutzung). |

Diese Felder werden in der **gleichen Field-Responsibility-Matrix** verwaltet wie die übrigen Felder, d. h. pro Feld wird festgelegt, welche Rolle informieren bzw. freigeben muss. Vorschlag für die Matrix dieser ergänzenden Felder:

| Feld | BR | IT-Sec | DSB | App-Mgr | App-Op | LizMgmt |
|---|---|---|---|---|---|---|
| Application Owner | I | I | I | **F** | I | I |
| Application Owner Stellv. | I | I | I | **F** | I | I |
| IT Application Owner | I | I | I | I | **F** | I |
| IT App Owner Stellv. | I | I | I | I | **F** | I |
| BIT-/FC-Kategorie | I | I | I | **F** | I | I |
| Beschreibung | I | I | I | **F** | I | I |
| Wo installiert | I | **F** | I | I | **F** | I |

### 4a.2 Systemkategorie nach Mitbestimmungsrelevanz (A–D)

**Pflichtfeld am Antrag.** Die gewählte Kategorie steuert die weitere Logik des Betriebsrats-Freigabezweigs.

| Kategorie | Bedeutung (im Wortlaut amedes) | Workflow-Konsequenz |
|---|---|---|
| **A** | Eine Leistungs- und/oder Verhaltenskontrolle ist technisch nicht möglich oder wird durch entsprechende Konfiguration dauerhaft unterbunden und es ist auch kein anderes Mitbestimmungsrecht berührt. | **Kein BR-Mitbestimmungsrecht.** Betriebsrats-Freigabe erfolgt als Information / Kenntnisnahme; bei Spalte I sowieso nur Info, bei Spalte F entfällt das Pflicht-Approval (auf "Kenntnisnahme" reduziert). |
| **B** | Eine Leistungs- und/oder Verhaltenskontrolle ist zwar technisch möglich, wird aber nicht bezweckt. | **Reguläre BR-Freigabe** wie bisher (F-Felder müssen explizit freigegeben werden). Hinweis im UI: "Nicht-Bezweckung schriftlich bestätigt? Konfigurations-Nachweis vorhanden?". |
| **C** | Die technische Einrichtung/Software ist zur Leistungs- und/oder Verhaltenskontrolle bestimmt. | **Erweiterter BR-Workflow.** Voraussetzung: Abschluss einer separaten **Betriebsvereinbarung**. App fordert Upload der unterzeichneten BV als Anhang; Final-Freigabe nur, wenn Anhang gesetzt und BR explizit freigegeben hat. |
| **D** | Aus sicherheitstechnischen Gründen umgehend erforderlich – amedes setzt um, GBR wird nachträglich informiert. | **Notfall-/Expedited-Workflow.** Antrag kann mit verkürzter Begründung sofort auf "vorläufig freigegeben" gesetzt werden; im Hintergrund wird automatisch ein **Nachgenehmigungs-Vorgang** für den GBR erzeugt mit Frist (z. B. 30 Tage). |

#### Validierungsregeln zur Systemkategorie

- Pflichtfeld bei Antragstellung; Auswahl A/B/C/D zwingend.
- Bei Wahl **C**: Anhang "Betriebsvereinbarung" wird Pflichtfeld, sonst ist Submit blockiert.
- Bei Wahl **D**: nur Application Owner und IT Application Owner gemeinsam dürfen diese Kategorie freischalten (Vier-Augen-Prinzip), Begründung Pflicht; Audit-Eintrag mit höherer Stufe; automatische Reminder an GBR + Geschäftsführung.
- **Kategorie-Wechsel** im Lebenszyklus eines Antrags ist erlaubt, erzeugt aber zwingend eine neue Revision sowie Reset der BR-Approvals.

### 4a.3 Anwendungsbereich (Section "Anwendungsbereich")

Aus dem amedes-Warenkorb-Formular wird die Sektion **„Anwendungsbereich"** übernommen und logisch der Frageliste angegliedert (entspricht inhaltlich teilweise Frage 4.3 und 4.4). Die App fasst die Felder in einer dedizierten UI-Sektion zusammen und vermeidet Doppelerfassung durch Mapping auf die bestehenden Felder.

## 5. Funktionale Anforderungen

### 5.1 Antragslebenszyklus

```
[Entwurf / Draft]  ◄──────────── Zwischenspeichern jederzeit
   │ Antragsteller füllt aus     (auch unvollständig, kein Versand!)
   │ kann pausieren und später   Auto-Save alle 30 s
   │ weitermachen, beliebig oft
   ▼
[Eingereicht]      (erst hier werden alle Abteilungen informiert)
   │ Automatischer Versand an alle F-Rollen
   ▼
[In Prüfung] ◄─────────────────────────────┐
   │                                       │ "Änderung erforderlich"
   │ Pro Rolle: Felder durchgehen          │ → zurück zum Antragsteller
   │ Status pro Feld:                      │
   │   • In Bearbeitung                    │
   │   • In Prüfung                        │
   │   • Abgelehnt (mit Kommentar Pflicht) ┘
   │   • Freigegeben
   ▼
[Alle Rollen vollständig freigegeben?]
   │ ja                       │ nein, mind. eine "Abgelehnt"
   ▼                          ▼
[Final freigegeben]        [Abgelehnt]
   │
   ▼
[Im Applikationsverzeichnis aktiv]
```

### 5.1a Entwurfsmodus / Zwischenspeichern

Der Antragsteller kann den Antrag jederzeit als **Entwurf** speichern und später weiterbearbeiten — ohne dass irgendeine Freigabe-Rolle informiert wird.

- **Auto-Save** alle 30 Sekunden bei aktiver Bearbeitung; sichtbarer Status ("Gespeichert vor 12 Sek.").
- **Manueller Button** „Speichern und schließen" → kehrt zur Antragsliste zurück.
- **Pflichtfeld-Validierung greift NICHT im Entwurfsmodus** — nur beim aktiven „Einreichen".
- Entwürfe sind ausschließlich für Antragsteller (und seine bewusst eingeladenen Mitbearbeiter) sichtbar; **keine** Sichtbarkeit für Freigabe-Rollen, **keine** Reminder-Erzeugung, **keine** E-Mail-Benachrichtigung.
- **Mehrere Mitbearbeiter:** Antragsteller kann optional weitere Personen einladen (Editier-Recht auf den Entwurf). Concurrent Editing wird über optimistic locking + Live-Indikator („Anna bearbeitet gerade Sektion 4") aufgelöst.
- **Entwurfs-Versionierung:** auch im Entwurfsmodus werden Revisionen geschrieben (Feldänderungen mit Zeitstempel und Bearbeiter), damit auch der Erstellungsverlauf nachvollziehbar bleibt.
- **Lebensdauer:** Entwürfe bleiben unbegrenzt erhalten. Nach 6 Monaten Inaktivität: Erinnerung an Antragsteller („Entwurf XY ist seit 6 Monaten nicht bearbeitet — weiter, archivieren oder löschen?").
- **Vorschau-Modus:** „Antrag-Vorschau" (read-only) zeigt, wie der Antrag den Freigebern erscheinen würde.
- **Pflichtfeld-Indikator:** im Entwurfsmodus wird angezeigt, **wie viele Pflichtfelder noch fehlen**, ohne den Speichervorgang zu blockieren.
- **Zurückziehen nach Submit nicht erlaubt** — wer einreicht, hat den Prozess gestartet. Korrekturen erfolgen ausschließlich über den regulären Rückweisungs-/Kommentar-Workflow. (Ausnahme: Admin kann auf Antrag manuell zurückziehen, mit Audit-Eintrag.)

### 5.2 Feldstatus pro Rolle

Pro Feld **und pro freigebender Rolle (F)** existiert ein eigener Status:

- **In Bearbeitung** (Default, sobald Antragsteller schreibt)
- **In Prüfung** (Antrag eingereicht, Rolle hat begonnen zu prüfen)
- **Abgelehnt** (Pflicht: Kommentar)
- **Freigegeben** (optional: Kommentar)

Pflichtfelder pro Rolle (Spalte F-Markierungen) müssen zwingend "Freigegeben" sein, damit der Gesamtantrag final freigegeben wird.

### 5.3 Kommentare und Threading

- Pro Feld kann jede F-Rolle einen **Kommentar-Thread** anlegen.
- Der Antragsteller kann pro Thread antworten.
- Kommentare sind nicht editierbar (nur löschbar durch Admin), aber als „bearbeitet" markierbar.
- @-Mentions optional (Phase 2).

### 5.4 Revisionierung

Jede Änderung erzeugt eine neue Revision:

- **Granularität:** Feldebene (jedes geänderte Feld → neue Revision).
- **Inhalt:** alter Wert, neuer Wert, Benutzer, Zeitstempel, Kommentar (optional bei Antragsteller).
- **Snapshot:** Pro Antragsänderung wird zusätzlich ein Vollsnapshot des Antrags persistiert (für Audit-Anzeige).
- **Diff-View:** UI zeigt vorherige vs. aktuelle Version pro Feld an.
- **Unveränderlich:** Revisionen können nicht gelöscht werden (außer durch Admin mit Auditprotokoll).

### 5.5 Audit Log

Separates, append-only Log für sicherheitsrelevante Aktionen:

- Login/Logout
- Status-Änderung (welche Rolle, welches Feld, alt → neu)
- Freigabe/Ablehnung (wer, wann, Kommentar)
- Antragsstatus-Änderungen
- Rollenzuweisungen, Reminder-Versand

Das Audit Log ist **unabhängig** von der fachlichen Revisionierung und für Auditoren read-only zugänglich.

### 5.6 Erinnerungen (Reminder Engine)

- Konfiguration durch Admin: pro Rolle eine Standardfrequenz (z. B. 3 Tage).
- Trigger: Antrag liegt seit X Tagen ohne Statusänderung bei einer Rolle.
- Eskalationsstufen:
  - **Stufe 1** (nach 3 Tagen): E-Mail an alle Mitglieder der Rolle + Verteilerliste
  - **Stufe 2** (nach 7 Tagen): zusätzlich E-Mail an Antragsteller + Vorgesetzte:n der Rolle (optional)
  - **Stufe 3** (nach 14 Tagen): E-Mail an Admin/Eskalationsmanager
- Implementierung: Cron-Job/Scheduler (z. B. APScheduler bei Python, BullMQ bei Node.js) der täglich 1× alle offenen Anträge prüft.
- Reminder werden im Audit Log und in einer eigenen Tabelle festgehalten.
- "Schweigeperiode": Antragsteller kann nicht mehr als 1× pro 24 h aktiv erinnern.

### 5.7 Applikationsverzeichnis

- Separater Bereich, der **alle final freigegebenen** Anwendungen tabellarisch listet.
- **Importmodus:** Bestehende Altsysteme können direkt eingetragen/editiert werden, ohne den vollen Freigabeworkflow zu durchlaufen (Status: "Bestand – importiert"). Diese Einträge sind als solche gekennzeichnet.
- **Edit:** Bei Änderungen an einer bereits freigegebenen Anwendung wird ein **Änderungsantrag** erzeugt – der dann wieder den (ggf. verkürzten) Freigabeprozess durchläuft.
- Felder im Verzeichnis sind die gleichen wie im Antrag plus Statusfelder (z. B. "produktiv seit", "letzte Rezertifizierung", "verantwortlicher Bereich").
- Suche, Filter, Export (CSV, Excel, PDF).

### 5.8 Berichte / Export

- Export eines abgeschlossenen Antrags als PDF (audit-tauglich, mit Freigabesignaturen + Zeitstempeln).
- Export des Applikationsverzeichnisses als CSV/Excel (z. B. für Audit, Lizenzmanagement).
- Standardberichte: offene Anträge pro Rolle, Durchlaufzeit pro Rolle, abgelehnte Anträge mit Begründung.

### 5.9 Suche & Filter

- Volltextsuche über Anträge und Verzeichnis.
- Filter nach Status, Rolle, Antragsteller, Hersteller, Kategorie, Zeitraum.

## 6. Datenmodell (logisch)

### 6.1 Kernentitäten

```
User (Benutzer)
 ├── id (UUID)
 ├── name, email
 ├── status (active, disabled)
 ├── created_at, updated_at
 └── n:m → Role

Role
 ├── id (enum: REQUESTER, BETRIEBSRAT, IT_SECURITY, DATA_PROTECTION,
 │                APP_MANAGER, APP_OPERATION, LICENSE_MGMT, ADMIN, AUDITOR)
 └── notification_email (Verteilerliste)

FieldDefinition (Stammdaten – die "Spalten" der Excel)
 ├── id, key (z. B. "produkt.hersteller")
 ├── category, label, description, reason (Erläuterung, Grund)
 ├── obligation (Pflicht / Optional / Bedingt)
 ├── help_text (vereinfachter Hilfetext, s. u.)
 ├── input_type (text, longtext, date, number, enum, yesno)
 ├── enum_values (JSON, optional)
 ├── conditional_visibility (Regel, z. B. "nur wenn datenschutz.personenbezogene = ja")
 ├── order (Sortierreihenfolge)
 └── responsibility_matrix → 1:n FieldResponsibility

FieldResponsibility (welche Rolle braucht welches Feld – aus Excel-Spalten I–N)
 ├── field_id, role_id
 └── responsibility (INFO | APPROVAL)        // I oder F

ApplicationRequest (Antrag)
 ├── id, title, requester_id
 ├── status (DRAFT, SUBMITTED, IN_REVIEW, CHANGES_REQUESTED,
 │           APPROVED, REJECTED, PROVISIONALLY_APPROVED  // Kategorie D)
 ├── system_category (A | B | C | D)                     // Mitbestimmung
 ├── application_owner_id (User)
 ├── application_owner_deputy_ids (User[])
 ├── it_application_owner_id (User)
 ├── it_application_owner_deputy_ids (User[])
 ├── bit_fc_category_ids (BitFcCategory[])               // Multi-Select
 ├── short_description (varchar 280)
 ├── installation_location (text)
 ├── operating_agreement_attachment_id (File, NULL)      // Pflicht bei Kategorie C
 ├── post_approval_due_date (date, NULL)                 // bei Kategorie D
 ├── created_at, submitted_at, completed_at
 ├── current_revision_id

BitFcCategory (Stammdaten)
 ├── id, name, description, parent_id (Hierarchie möglich)

SystemCategoryDefinition (Stammdaten – fix verdrahtet A/B/C/D)
 ├── code, label, description, requires_bv_attachment, requires_post_approval

Attachment (Dateianhang)
 ├── id, application_request_id, filename, mime_type,
 │   storage_uri, uploaded_by, uploaded_at, purpose
 │   (z. B. OPERATING_AGREEMENT, OFFER, SECURITY_CONCEPT)
 └── 1:n → FieldValue, 1:n → Revision, 1:n → ApprovalDecision, 1:n → Comment

FieldValue (aktueller Wert eines Felds für einen Antrag)
 ├── application_request_id, field_id
 ├── value (TEXT / JSON)
 ├── updated_by, updated_at

ApprovalDecision (Status pro Feld pro Rolle)
 ├── application_request_id, field_id, role_id
 ├── status (IN_PROGRESS, IN_REVIEW, REJECTED, APPROVED)
 ├── decided_by (User), decided_at
 └── 1:n → Comment

Comment (Threaded)
 ├── id, parent_id (NULL = Wurzelkommentar pro Feld+Rolle)
 ├── application_request_id, field_id, role_id (kann NULL sein bei Antragsteller-Antwort)
 ├── author_id, body, created_at, edited_at

Revision (Versionierung)
 ├── id, application_request_id, revision_number
 ├── created_by, created_at
 ├── change_summary (kurz)
 └── snapshot (JSONB: Vollabbild aller FieldValues + Decisions zum Zeitpunkt)

AuditLog
 ├── id, occurred_at
 ├── actor_id (User), actor_role
 ├── action (LOGIN, FIELD_UPDATED, STATUS_CHANGED, APPROVAL_GIVEN, COMMENT_ADDED, ...)
 ├── target_type, target_id
 └── payload (JSONB, z. B. before/after)

Reminder
 ├── id, application_request_id, role_id
 ├── stage (1|2|3), sent_at, sent_to (JSON)

CatalogEntry (Applikationsverzeichnis)
 ├── id, source (FROM_REQUEST | IMPORTED)
 ├── application_request_id (NULL bei Import)
 ├── name, vendor, version, owner_role, status (ACTIVE, RETIRED)
 ├── effective_from, last_recertified_at
 └── fields (JSONB für die Anzeige)

NotificationTemplate
 ├── id, key (z. B. "REMINDER_STAGE_1")
 ├── subject, body (Markdown), language
```

### 6.2 Datenbank: PostgreSQL

Begründung: stabile Revisionierungsstrategie via JSONB für Snapshots, Volltextsuche, ausgereiftes Tooling.
Empfohlene Erweiterungen:

- `pgcrypto` (UUIDs)
- `pg_trgm` (Volltextsuche)
- `temporal_tables` (optional, für built-in History)

## 7. Architektur

### 7.1 Empfohlener Tech-Stack

| Schicht | Empfehlung | Alternative |
|---|---|---|
| Frontend | **Next.js (React, TypeScript)** + Tailwind + shadcn/ui | Vue 3 / Nuxt |
| Backend | **FastAPI (Python 3.12)** | NestJS (TypeScript) |
| ORM | SQLAlchemy 2.x + Alembic | Prisma (bei Node) |
| DB | **PostgreSQL 16** | – |
| Auth (Phase 1) | E-Mail + Passwort (Argon2), JWT | – |
| Auth (Phase 2) | **Keycloak** via OIDC | Azure Entra ID |
| Background Jobs | **APScheduler** + Redis Queue | Celery |
| E-Mail-Versand | SMTP (intern) bzw. Microsoft Graph API | – |
| Container | Docker, betrieben auf bestehendem Kubernetes-Cluster | – |
| CI/CD | GitLab CI / GitHub Actions | – |
| Logging | Strukturiertes JSON-Logging → Loki / ELK | – |
| Observability | OpenTelemetry, Prometheus, Grafana | – |

Begründung Python+FastAPI: schnelle Umsetzung, hervorragende Validierung mit Pydantic, gut dokumentiert, optimal für Workflow-Logik.

### 7.2 Komponenten-Übersicht

```
            ┌─────────────────────────────┐
            │       Browser (Next.js)     │
            └──────────────┬──────────────┘
                           │ HTTPS, JWT
            ┌──────────────▼──────────────┐
            │      API (FastAPI)          │
            │  • Auth & RBAC              │
            │  • Workflow-Engine          │
            │  • Validierung              │
            │  • Audit / Revision         │
            └──┬─────────────┬───────┬────┘
               │             │       │
       ┌───────▼──┐   ┌──────▼──┐  ┌─▼──────────┐
       │PostgreSQL│   │  Redis  │  │  SMTP /    │
       │          │   │ (Queue) │  │ MS Graph   │
       └──────────┘   └─────────┘  └────────────┘
                           │
                  ┌────────▼─────────┐
                  │ Reminder Worker  │
                  │ (APScheduler)    │
                  └──────────────────┘
```

### 7.3 Sicherheitsanforderungen

- **Authentifizierung:** Phase 1 lokal (Argon2-Hashes), Phase 2 OIDC/Keycloak; in beiden Phasen MFA (TOTP) für Admin- und Freigaberollen.
- **Autorisierung:** Policy-basiertes RBAC im Backend (z. B. via Casbin oder eigene Decorators).
- **Datenschutz:** TLS 1.3 only, HSTS, sichere Cookies (Secure, HttpOnly, SameSite=strict).
- **OWASP Top 10:** CSRF-Token, Output-Encoding, parametrisierte Queries (ORM), Rate-Limiting (z. B. SlowAPI).
- **Geheimnisse:** ausschließlich aus Vault / Env-Variablen, niemals im Repo.
- **Logging:** Personenbezogene Daten in Logs minimieren (User-IDs ja, Klartextnamen nein).
- **Backup:** tägliche DB-Backups, RTO 1h, RPO 1h (analog zu den definierten SLAs der Plattform).

### 7.4 DSGVO-Aspekte der App selbst

- Verarbeitung personenbezogener Daten: ausschließlich der App-Nutzer (Mitarbeitende).
- Rechtsgrundlage: Art. 6 Abs. 1 lit. b DSGVO + § 26 BDSG.
- Löschkonzept: Anträge dauerhaft (Audit), Benutzerkonto bei Austritt → Pseudonymisierung nach 6 Monaten.
- Auskunfts- und Löschanträge: über Admin-UI abbildbar (Datenschutz-Workflow).

## 8. UI/UX-Konzept

### 8.1 Hauptbereiche

1. **Dashboard** (rollenabhängig)
   - Antragsteller: meine Anträge, offene Rückfragen
   - Freigeber: meine offenen Freigaben (sortiert nach Alter, Stufe-2-Reminder hervorgehoben)
   - Admin: Systemkennzahlen, eskalierte Anträge
2. **Antragsformular** (Wizard mit Sektionen analog zur Excel-Kategorien-Struktur)
   - Sticky-Sidebar mit Fortschritt pro Kategorie
   - Pro Feld: Label, Hilfetext (collapsible), Eingabe, Statuszeile pro F-Rolle, Kommentar-Bereich
   - Inline-Diff-Hinweis, wenn der Wert seit letzter Freigabe geändert wurde
   - **Reihenfolge der Sektionen:**
     1. Antragsteller (Name, E-Mail, Abteilung)
     2. **Stammdaten der Anwendung** (Application Owner + Stellv., IT App Owner + Stellv., BIT-/FC-Kategorie, Beschreibung)
     3. **Systemkategorie** (Pflicht-Dropdown A/B/C/D mit eingeblendeter Beschreibung; bei C: Upload-Feld für Betriebsvereinbarung; bei D: Vier-Augen-Bestätigung + Begründung)
     4. Produkt (Hersteller, Name, Version, Beschreibung, Wo installiert)
     5. Projekt (Einführungszeitpunkt, auszurollende Standorte, Softwareauswahl)
     6. Anwendungsbereich (Datenschutz-Voraussetzung, Anwendung, Anwender, Rechtemanagement, Schulung, Mitarbeiterdaten, Leistungsüberwachung)
     7. Schnittstellen
     8. Datenschutz (Verarbeitungsverzeichnis-Felder)
     9. Lizenzen
     10. Betrieb
     11. Cloud (bedingt)
     12. Service Level Agreements
     13. Kosten
     14. Sonstiges
3. **Freigabeansicht** (Reviewer-Modus)
   - Liest sich wie das Antragsformular, aber mit prominentem Status-Dropdown pro Feld
   - Bulk-Aktion: "Alle nicht-relevanten Felder als gesehen markieren"
4. **Revisionsansicht**
   - Zeitstrahl + Diff-Viewer (alt/neu nebeneinander)
5. **Applikationsverzeichnis**
   - Tabelle mit Suche/Filter
   - Detailseite je Eintrag mit "Änderungsantrag erstellen"-Button
   - Importmodus für Bestand
6. **Administration**
   - Benutzer/Rollen
   - Reminder-Konfiguration
   - Feld-Templates (Hilfetexte, Pflichtangaben pflegen)
   - Audit-Log-Ansicht

### 8.2 Statusbadges (UI)

- Grau: In Bearbeitung
- Blau: In Prüfung
- Grün: Freigegeben
- Rot: Abgelehnt
- Gelb: Reminder Stufe 2/3 aktiv

### 8.3 Barrierefreiheit & i18n

- WCAG 2.1 AA (Tastatur-Navigation, ARIA-Labels, Kontrast).
- Zunächst Deutsch; Architektur i18n-fähig (next-intl/i18next) für späteres Englisch.

## 9. Workflow-Logik im Detail

### 9.1 Validierung beim Einreichen

Beim Klick auf "Antrag einreichen":

1. Alle Pflichtfelder sind ausgefüllt? (Beachtung der `obligation` und `conditional_visibility`)
2. **Systemkategorie ist gewählt (A/B/C/D).** Bei C ist Anhang "Betriebsvereinbarung" gesetzt. Bei D ist Bestätigung durch Application Owner + IT Application Owner vorhanden.
3. Statusübergang: `DRAFT → SUBMITTED → IN_REVIEW` (bei Kategorie D zusätzlich `→ PROVISIONALLY_APPROVED` mit Nachgenehmigungs-Frist).
4. Alle F-Rollen erhalten E-Mail mit Direktlink.
5. Pro F-Rolle und pro betroffenem Feld wird ein `ApprovalDecision` mit Status `IN_PROGRESS` angelegt.

### 9.1a Systemkategorie-abhängige Workflow-Logik

Die gewählte **Systemkategorie A–D** verzweigt den Freigabezweig des Betriebsrats:

```
        ┌────────────────────────┐
        │  Antrag eingereicht    │
        └────────────┬───────────┘
                     ▼
            ┌────────────────┐
            │ Systemkategorie│
            └─┬───┬───┬─────┬┘
              │   │   │     │
              ▼   ▼   ▼     ▼
              A   B   C     D
              │   │   │     │
              │   │   │     ▼
              │   │   │  Provisorische
              │   │   │  Freigabe (sofort)
              │   │   │  + Nachgenehmigung
              │   │   │     im Hintergrund
              │   │   ▼
              │   │  BV-Anhang Pflicht
              │   │  → BR-Vollprüfung
              │   ▼
              │  Reguläre BR-Prüfung
              ▼
        BR = nur Information /
        Kenntnisnahme
              │
              └────► weitere Rollen wie gewohnt
```

- **A:** Betriebsrats-Approval-Decisions werden automatisch auf "Kenntnisnahme genommen" gesetzt, ein:e BR-Vertreter:in muss aber aktiv bestätigen ("Zur Kenntnis genommen"). Andere F-Rollen wie gewohnt.
- **B:** Standard-Workflow ohne Sonderlogik. UI-Hinweis: "Konfiguration zur Unterbindung der Leistungs-/Verhaltenskontrolle dokumentieren?".
- **C:** Anhang Betriebsvereinbarung ist Pflicht. UI sperrt Submit, solange kein Anhang. BR-Approval erfolgt erst nach Anhangs-Sichtung; im Approval-Kommentar-Thread ist Bezug auf BV-Aktenzeichen Pflicht.
- **D:** Sonderzweig "Notfall". Antrag erhält sofort den Status `PROVISIONALLY_APPROVED`; gleichzeitig wird automatisch ein Nachgenehmigungs-Vorgang am GBR adressiert mit konfigurierbarer Frist (Default 30 Tage). Reminder Stufe 2 wird hier verkürzt (z. B. 5 Tage) ausgelöst. Nach Ablauf ohne Reaktion: Eskalation an Geschäftsführung.

### 9.1b Auto-Befüllung „Verantwortlicher Bereich (fachlich)"

Sobald `application_owner_id` und `bit_fc_category_ids` gesetzt sind, schlägt die App den Wert für Frage 4.2 („Verantwortlicher Bereich") automatisch vor (übernimmt Owner-Daten). Antragsteller können den Vorschlag überschreiben.

### 9.2 Statusübergänge pro Feld (Reviewer-Sicht)

Eine Rolle kann pro Feld:

- den Status setzen (`IN_PROGRESS` → `IN_REVIEW` → `APPROVED`/`REJECTED`)
- bei `REJECTED`: Kommentar Pflicht
- bei `APPROVED`: Kommentar optional

### 9.3 Antragsteller-Reaktion auf Ablehnung

- Antragsteller bekommt Aggregat-Mail: „X Felder benötigen Nachbesserung".
- Felder, die abgelehnt wurden, sind im Formular rot markiert; Antragsteller kann dort den Wert bearbeiten **oder** im Kommentar-Thread antworten.
- Sobald Antragsteller "Erneut zur Prüfung freigeben" klickt: betroffene Approval-Decisions gehen wieder auf `IN_REVIEW`, betroffene Rollen werden benachrichtigt. Andere F-Rollen, deren Felder unverändert sind, behalten ihren Status `APPROVED`.

### 9.4 Final-Freigabe-Logik

- Antrag erhält Status `APPROVED`, sobald für **jede** F-markierte Zelle der Field-Responsibility-Matrix mindestens **eine** der Rollen-Mitgliedspersonen den Status `APPROVED` gesetzt hat.
- Trigger: bei jedem Statuswechsel wird die Vollständigkeit geprüft (transactional).
- Bei `APPROVED` automatisch: Eintrag im Applikationsverzeichnis (`source = FROM_REQUEST`).

### 9.5 Reminder-Logik (Pseudocode)

```python
# tägliches Cron-Job
for request in active_requests():
    for role in request.pending_roles():
        days = days_since_last_action(request, role)
        if days >= 14 and not stage_3_sent:
            send_reminder(stage=3, to=admin_escalation_list)
        elif days >= 7 and not stage_2_sent:
            send_reminder(stage=2, to=role.members + role.distribution_list + request.requester)
        elif days >= 3 and not stage_1_sent_today:
            send_reminder(stage=1, to=role.members + role.distribution_list)
```

## 10. API-Skizze (REST)

> Hinweis: Endpoints versioniert unter `/api/v1`. Authentifizierung per Bearer-JWT. Antworten als JSON.

| Methode | Pfad | Zweck |
|---|---|---|
| `POST` | `/auth/login` | Login (Phase 1) |
| `GET`  | `/auth/me` | Aktueller Benutzer + Rollen |
| `GET`  | `/users` | Liste (Admin) |
| `POST` | `/users` | Anlegen (Admin) |
| `GET`  | `/roles` | Rollen + Mitglieder |
| `POST` | `/roles/{id}/members` | Person zur Rolle hinzufügen |
| `GET`  | `/fields` | Stammdaten der Felder |
| `GET`  | `/requests` | Liste (gefiltert) |
| `POST` | `/requests` | Neuer Antrag (Draft) |
| `GET`  | `/requests/{id}` | Vollansicht inkl. Decisions |
| `PATCH`| `/requests/{id}/fields/{fieldKey}` | Feldwert ändern |
| `POST` | `/requests/{id}/submit` | Einreichen |
| `POST` | `/requests/{id}/decisions` | Status pro Feld+Rolle setzen |
| `POST` | `/requests/{id}/comments` | Kommentar (Reply optional) |
| `GET`  | `/requests/{id}/revisions` | Revisionsliste |
| `GET`  | `/requests/{id}/revisions/{rev}` | Snapshot |
| `GET`  | `/catalog` | Applikationsverzeichnis |
| `POST` | `/catalog/import` | Bestand importieren |
| `PATCH`| `/catalog/{id}` | Eintrag bearbeiten |
| `GET`  | `/audit-log` | nur Admin/Auditor |
| `GET`  | `/reports/throughput` | Kennzahlen |

## 11. Vereinfachung der bestehenden Hilfetexte (Vorschläge)

Die Hilfetexte aus der Excel sind teils sehr lang oder doppelt. Vorschlag: kurzer **Helptext** (max. 2 Zeilen, immer sichtbar) + **Erweiterter Hinweis** (collapsible, mit DSGVO-Bezug für Auditor:innen). Auswahl:

| Feld | Bisheriger Erläuterungstext | Vorschlag (kurz) | Erweiterter Hinweis |
|---|---|---|---|
| 2.3 Beschreibung des Systems | "Welche Eigenschaften hat das System? Bitte nicht die Anwendung des Systems beschreiben, sondern das System als solches." | "Was **ist** die Software? (nicht: wie wird sie genutzt?)" | "Beispiel: 'Open-Source-IAM-Plattform mit OIDC/SAML', nicht 'wir loggen uns damit ein'." |
| 4.3 Anwendung des Systems | "Wie und Wozu wird das System bei amedes genutzt werden? Wie werden Arbeitsabläufe verändert?" | "Wofür wird das System bei amedes genutzt – und was ändert sich dadurch im Alltag?" | Bezug zu Verarbeitungstätigkeit gem. DSGVO bleibt erhalten; Beispiele optional einblendbar. |
| 4.5 Betroffene Personen | "Welche Personen / Bereiche / Abteilungen sind von der Einführung betroffen?" | "Wer ist betroffen? (Mitarbeitende, Patienten, Externe)" | DSGVO Art. 30 – Kategorien betroffener Personen. |
| 4.7 Rechtemanagement | "Gibt es eine Rechtemanagement in dem die Zugangsrechte geregelt sind?" | "Wie werden Zugriffsrechte vergeben? (Rollen, Gruppen, AD-Anbindung?)" | – |
| 4.9 Eignung Leistungsüberwachung | (lang) | "Kann das System Leistung/Verhalten von Mitarbeitenden überwachen? Wenn ja: wie wird Missbrauch verhindert?" | Mitbestimmungspflichtig nach BetrVG. |
| 5.1 Umsysteme & Daten | (lang) | "Welche Schnittstellen gibt es zu welchen Systemen – mit welchen Daten?" | Besonders relevant bei personenbezogenen Daten. |
| 6.x Datenschutz-Block | jeweils mit "Gesetzliche Anforderung der DSGVO." | Einleitungssatz pro Block + kurze, einheitliche Hinweise pro Feld | Verweis auf das amedes-Verarbeitungsverzeichnis statt Wiederholung. |
| 8.3 amedes IT Betrieb | "Welche Verantwortungen darüberhinaus soll die amedes IT im Betrieb übernehmen?" | "Was übernimmt die amedes-IT im Betrieb (Updates, Backup, Monitoring, …)?" | – |
| 9.1 Cloudbasiertes System | (lang) | "Wird das System über Internet/Cloud bereitgestellt? (Ja/Nein)" | Folgefragen 9.2/9.3 nur wenn Ja. |
| 10.x SLAs | "Die IT Organisation muss…" wiederholt sich | Einmaliger Sektionseinleiter, dann Frage knapp | – |
| 12.1 Sonstiges | "Sonstige Anmerkungen" | "Anmerkungen oder Risiken, die sonst nicht erfasst sind?" | – |

**Allgemeine Hinweise zu Vereinfachung:**

- Konsequente Trennung "Frage" (eine Zeile) vs. "Hilfe" (collapsible).
- Beispiele in eigenes UI-Element ("Beispiel ansehen"), nicht im Fließtext.
- Doppelte Schreibweisen vereinheitlichen ("Erläuterung" vs. "Erläutgerung" usw.).
- Tippfehler in Vorlage korrigieren (z. B. "Verarbeitungstätigkeit", "Übermittleln", "Application Operatior").

## 12. Implementierungsfahrplan (Vorschlag)

### Phase 0 – Setup (1 Sprint, ~1 Woche)

- Repo-Setup, Pre-commit, Linter, Container, CI/CD-Skelette.
- DB-Schema (Alembic-Migration v1).
- Feld-Stammdaten via Seed aus Excel-Import-Skript.

### Phase 1 – Antragsworkflow MVP (3–4 Sprints)

- Lokale Authentifizierung, Benutzer/Rollen-CRUD.
- Antragsformular (Draft → Submit).
- Reviewer-Sicht mit Status-Dropdown und Kommentaren.
- Final-Freigabe-Logik.
- Basisrevisionierung (Snapshot pro Submit).
- E-Mail-Notifications (synchron).

### Phase 2 – Reminder, Audit, Verzeichnis (2–3 Sprints)

- Reminder-Engine mit Eskalationsstufen.
- Audit Log + Auditor-Rolle.
- Applikationsverzeichnis inkl. Bestandsimport.
- PDF-Export.

### Phase 3 – Keycloak-Integration & UX-Feinschliff (1–2 Sprints)

- OIDC, SSO, Rollen-Mapping aus Keycloak-Gruppen.
- @Mentions in Kommentaren.
- Erweiterte Berichte / Dashboard-Widgets.
- Optional: Webhooks für ITSM (z. B. Jira Service Management).

### Phase 4 – Härtung

- Penetrationstest, Last- und Backup-Test.
- Datenschutz-Review.
- Schulung & Dokumentation.

## 13. Akzeptanzkriterien (Auszug für QA)

- [ ] Antragsteller kann Antrag anlegen, speichern, einreichen.
- [ ] Pflichtfeldvalidierung beim Einreichen funktioniert.
- [ ] Pro F-Rolle ist Statussetzung pro Feld möglich; Ablehnung erzwingt Kommentar.
- [ ] Antrag wird genau dann final freigegeben, wenn für **jedes F-Feld** mindestens eine Person der jeweiligen Rolle "Freigegeben" gesetzt hat.
- [ ] Jede Wertänderung erzeugt eine Revision; alte Werte sind im UI sichtbar.
- [ ] Erinnerungen werden korrekt nach 3/7/14 Tagen ausgelöst und versendet.
- [ ] Audit Log enthält alle relevanten Aktionen.
- [ ] Applikationsverzeichnis kann Bestand importieren und bestehende Einträge bearbeiten.
- [ ] Rollen-Wechsel (Person verlässt Rolle) führt nicht zum Verlust historischer Freigaben.
- [ ] Login per OIDC/Keycloak (Phase 3) liefert konsistent dieselben Berechtigungen wie lokales Auth.

## 14. Risiken & Mitigation

| Risiko | Auswirkung | Mitigation |
|---|---|---|
| Komplexität der Per-Feld-Freigabe wird zur UX-Hürde | Niedrige Akzeptanz | Reviewer-Modus mit Bulk-Aktionen; sinnvolle Vorbelegung; Hilfetexte kurz halten |
| Antragsteller füllen Felder oberflächlich aus | Verzögerungen, Ping-Pong | Vorlagen pro Systemtyp, Beispiele direkt im UI, Plausibilitätschecks |
| Schweigen einer Rolle blockiert Prozess | Anträge bleiben hängen | Eskalationsstufen + Vertretungsregelung in Rollenmodell |
| Keycloak-Migration bricht bestehende Konten | Login-Ausfall | Phase 3 mit Schattenbetrieb; Rollen-Mapping vorab Trockenlauf |
| DSGVO-konforme Aufbewahrung der Audit-Daten | Compliance-Risiko | Klares Lösch-/Anonymisierungskonzept (s. 7.4), regelmäßige Reviews |
| Excel-Vorlage ändert sich nach Go-Live | Felder-Drift | Feld-Stammdaten versioniert, Migrationspfad für neue/entfernte Felder |

## 15. Offene Fragen an den Auftraggeber

1. Soll **eine** Person pro Rolle reichen ("ODER-Verknüpfung") oder müssen **alle** zugeordneten Personen freigeben ("UND-Verknüpfung")?
2. Sollen Anträge nach finaler Freigabe in regelmäßigen Abständen rezertifiziert werden (z. B. jährlich)?
3. Wer ist Eskalationsempfänger der Stufe 3 (Admin-Mailadresse)?
4. Welche Sprachen werden langfristig unterstützt (nur DE? auch EN für externe Audits?)?
5. Wo wird die App betrieben – Kubernetes (vorgesehen) oder klassisches VM-Setup?
6. SSO-Domain: ist der Keycloak-Realm "amedes" bereits vorgesehen, oder eigener Realm für interne Tools?
7. Soll die App in bestehende ITSM (z. B. Jira Service Management) integriert werden?
8. E-Mail-Versand: zentral (SMTP-Relay) oder via Microsoft Graph?
9. Reminder-Frequenz: bestätige 3/7/14 Tage als Standard oder andere Werte gewünscht?
10. Bestandsimport: welche Datenquelle (CSV-Liste, bestehende SharePoint-Listen, alte Excel-Dateien)?

## 16. Hinweis zum Übergabe-Workflow an Claude Code

Empfehlung für die Übergabe:

1. Diesen Konzeptdoc als `SPEC.md` ins neue Repo legen.
2. Zusätzlich `CLAUDE.md` mit knappen Coding-Konventionen und Verweis auf die Spec ablegen.
3. Repo-Struktur (Vorschlag):

```
sysintro/
├── SPEC.md                     ← dieses Dokument
├── CLAUDE.md                   ← Coding-Konventionen
├── docker-compose.yml          ← lokale Entwicklung (Postgres, Redis, MailHog)
├── backend/                    ← FastAPI
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/               ← Config, Security
│   │   ├── domain/             ← Entitäten
│   │   ├── services/           ← Workflow, Reminder
│   │   ├── infra/              ← DB, Mail, Queue
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml
├── frontend/                   ← Next.js
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── package.json
├── infra/
│   ├── helm/                   ← Kubernetes-Charts
│   └── terraform/              ← optional
└── docs/
    ├── adr/                    ← Architectural Decision Records
    └── runbooks/
```

4. Erste Aufgabe an Claude Code: "Initialisiere das Repo gemäß SPEC.md, lege das Datenbankschema (Alembic) an, erzeuge Seed-Daten aus der Excel-Datei `Frageliste Systemeinführung und -änderung.xlsx`, und erstelle das API-Skelett mit Auth + User/Role-CRUD. Schreibe Tests."

---

**Ende des Konzepts.**
