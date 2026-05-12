# SysIntro – Präsentations-Storyboard

*Für Stakeholder-Präsentationen (15–25 Min). Reine Inhaltsstruktur,
keine Folien-Optik.*

---

## Slide 1 – Titel

**SysIntro – Digitale Software-Einführung bei amedes**

- Untertitel: „Von der Excel-Liste zum auditierbaren Workflow"
- Datum / Sprecher / Ansprechpartner

---

## Slide 2 – Ausgangslage

- Software-Einführungen heute: Excel-Liste + E-Mail-Abstimmung mit
  6 verschiedenen Rollen (Antragsteller, BR, IT-Security, Datenschutz,
  App-Manager, App-Betrieb, Lizenzen).
- Probleme:
  - Keine zentrale Nachvollziehbarkeit, **wer wann was entschieden hat**.
  - Wiederholte Rückfragen per E-Mail, keine Verknüpfung zur Frage selbst.
  - Anlagen liegen verteilt, Versionen unklar.
  - Reviewer wissen nicht, **welche Felder sie überhaupt prüfen sollen**.
  - Statistiken zu Bearbeitungszeit / Bottlenecks fehlen.

---

## Slide 3 – Ziel von SysIntro

- **Ein Formular, das sich an die Software anpasst** – pro Rolle nur
  die Felder, die sie betreffen.
- **Pro-Feld-Entscheidung statt Pauschal-Freigabe** – jede Rolle
  entscheidet feldgenau und kann Rückfragen anhängen.
- **Vollständiger Audit-Trail** – jede Änderung, jede Freigabe, jede
  Rückfrage ist mit Zeitstempel und Benutzer protokolliert.
- **Lebenszyklus** – DRAFT → SUBMITTED → IN_REVIEW → APPROVED /
  REJECTED, optional POC → Standard.

---

## Slide 4 – Rollen & Verantwortlichkeiten

| Rolle | Aufgabe | Beispiel-Feld |
|---|---|---|
| Antragsteller | Antrag stellen + ausfüllen | Hersteller, Beschreibung |
| Betriebsrat | Mitbestimmung (A/B/C/D) | Systemkategorie |
| IT-Security | Schutzbedarf, Risiko | Datenklassifikation |
| Datenschutz | DSFA, AVV | Personenbezug |
| App-Manager | Fachliche Eignung | Anwendungsfälle |
| App-Betrieb | Betreibbarkeit | Installation, Monitoring |
| Lizenzen | Kosten + Vertrag | Lizenzmodell |
| Admin | Fragenkatalog pflegen | – |

---

## Slide 5 – Workflow (visuell)

➜ Excalidraw-Diagramm `architecture.excalidraw` (Tab „Workflow").

Kernstationen:

```
   Antrag anlegen → Felder ausfüllen → Einreichen
        ▼                                   ▼
     Rückfragen ◀───── Reviewer pro Feld ──┘
        ▼                                   ▼
     Antwort                          Freigabe / Ablehnung
                                            ▼
                                  Systemkatalog (live)
```

---

## Slide 6 – Was läuft schon (Pilot)

- Dynamischer Fragenkatalog mit bedingten Feldern
- Auto-Save + Race-Condition-sicheres Einreichen
- Pro-Feld-Rückfragen mit synthetischem Konversations-Thread
- POC-Workflow mit Promotion zu Standard
- Reviewer-Statuschips mit Prioritäts-Farbcode
- Antrag zurückziehen + Entwurf löschen
- Revisionen ab Einreichung (alter Wert / neuer Wert)
- Admin-Oberfläche für Fragenkatalog
- Audit-Log append-only

(Live-Demo planbar mit Demo-Accounts.)

---

## Slide 7 – Architektur (Überblick)

➜ Excalidraw-Diagramm `architecture.excalidraw` (Tab „Architektur").

- **Frontend**: Browser, Tailwind + HTMX (kein SPA, kein Build-Tool)
- **Edge**: Cloudflare TLS + DDoS
- **App**: nginx → uvicorn → FastAPI (Python 3.13)
- **Logik**: `app/services/` (thin routes, fat services)
- **DB**: Pilot SQLite → Prod PostgreSQL 16
- **Auth**: Pilot lokal Argon2 → Prod Keycloak OIDC
- **Mail**: heute Stub → Prod SMTP/Graph

---

## Slide 8 – Go-Live-Bausteine

| # | Baustein | Status | Effort |
|---|---|---|---|
| 1 | Keycloak-OIDC | 🔴 Architektur fertig, Code offen | 5 PT |
| 2 | PostgreSQL | 🔴 Migration vorbereitet, Cutover offen | 3 PT |
| 3 | SMTP / Graph | 🟡 Service-Schnittstelle existiert | 2 PT |
| 4 | Monitoring | 🟡 Healthz vorhanden, Metriken offen | 2 PT |
| 5 | DSFA + Pen-Test | 🔴 in Planung | extern |

Details siehe [`GOLIVE.md`](GOLIVE.md).

---

## Slide 9 – Sicherheit (Highlights)

- Argon2 für lokale Passwörter (vor OIDC)
- JWT in HttpOnly + SameSite=Lax Cookie
- CSRF-Double-Submit
- Rate-Limit auf Login
- Audit-Log append-only
- File-Upload: MIME-Whitelist, 25 MB Max, UUID-Filenames
- Cloudflare-TLS + nginx-Reverse-Proxy

---

## Slide 10 – Datenmodell (Kernobjekte)

```
   User ────────────────┐
                        │
   Role ◀──────── UserRole
   Role ◀───── FieldResponsibility ────▶ FieldDefinition
                                              │
                                              ▼
   ApplicationRequest ─── FieldValue
        │ │ │
        │ │ └─▶ Comment (per-field thread)
        │ └─▶ ApprovalDecision (per-field × role)
        └─▶ Revision (post-submit edits)

   Attachment ──▶ ApplicationRequest
   SystemCategoryDefinition / BitFcCategory / Vendor (Stammdaten)
   AuditLog (append-only)
```

---

## Slide 11 – Roadmap

```
 Q2 2026 ─── Pilot-Härtung
   ↳ Keycloak, Postgres, SMTP, Pen-Test

 Q3 2026 ─── Go-Live Welle 1
   ↳ IT + Fachbereiche A/B/C

 Q4 2026 ─── Welle 2 + Reporting
   ↳ Auswertung Engpässe, Templates pro Software-Typ
```

---

## Slide 12 – Demo-Anker

Bei Live-Demo zeigen:

1. Antrag „SAP S/4HANA" öffnen → Felder zeigen.
2. Als Betriebsrat Rückfrage zu Kategorie B stellen.
3. Wechsel zum Antragsteller → Antwort eingeben → zurück.
4. Reviewer-Status-Chips erklären (Farbcode).
5. Audit-Log + Revisionen einer eingereichten Änderung zeigen.
6. Systemkatalog (freigegebene Systeme) zeigen.

---

## Slide 13 – Diskussion / Fragen

- Welche Rollen-Mappings braucht Keycloak konkret?
- Welcher Postgres-Cluster ist Ziel (eigener Server / managed)?
- Welche Empfänger-Listen für die Mail-Trigger?
- Welche Software-Typen sollen Welle 1 abdecken?
