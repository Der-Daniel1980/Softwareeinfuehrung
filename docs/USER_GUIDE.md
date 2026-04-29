# Anwender-Handbuch

Anleitung für die drei Hauptnutzergruppen: **Antragsteller**, **Freigeber**, **Administrator**.

---

## 1. Antrag stellen (Antragsteller)

### 1.1 Anmelden

1. Browser auf `https://<sysintro-domain>/login` öffnen
2. E-Mail + Passwort eingeben
3. **In der Demo:** auf einen der Quick-Fill-Buttons klicken (z. B. „requester")

### 1.2 Neuen Antrag erstellen

1. Im Dashboard auf **„Neuer Antrag"** (oder Menüpunkt **Anträge → + Neu**)
2. Aussagekräftigen Titel eingeben (z. B. „Einführung Microsoft Project Cloud")
3. **Speichern** → Du landest im Wizard

### 1.3 Wizard ausfüllen

Der Wizard hat **14 Sektionen**, links als Sticky-Sidebar sichtbar:

| Sektion | Inhalt |
|---|---|
| Stammdaten | Application Owner, IT-App-Owner, BIT/FC-Kategorie, Beschreibung, Installationsort |
| Systemkategorie | A / B / C / D — siehe Erläuterung im UI |
| Produkt | Hersteller, Name, Version, Beschreibung |
| Projekt | Einführungszeitpunkt, Standorte |
| Anwendung | Zweck, betroffene Personen, Rechtemanagement, Leistungsüberwachung |
| Schnittstellen | Umsysteme & Datenflüsse |
| Datenschutz | Personenbezug, Rechtsgrundlage, DPIA |
| Lizenzen | Modell, Anzahl |
| Betrieb | amedes-IT-Verantwortung, Backup |
| Cloud | Cloud-basiert ja/nein, Region |
| SLA | Verfügbarkeit |
| Kosten | Einmalig |
| Sonstiges | Anmerkungen |

#### Auto-Save

- Felder werden **automatisch beim Verlassen** des Inputs gespeichert
- Status-Anzeige rechts oben: „✓ Gespeichert"
- **Pflichtfeld-Zähler** zeigt, wie viele Pflichtfelder noch fehlen

#### Bedingte Felder

Manche Felder erscheinen nur unter bestimmten Bedingungen, z. B.:
- `Cloud-Region` nur, wenn `Cloud-basiert = Ja`
- `Rechtsgrundlage`, `DPIA` nur, wenn `Personenbezogene Daten = Ja`

#### Systemkategorie A–D

| Kategorie | Bedeutung | Folge |
|---|---|---|
| **A** | Keine Leistungs-/Verhaltenskontrolle | BR muss nur Kenntnisnahme bestätigen |
| **B** | Technisch möglich, nicht bezweckt | Standard-BR-Freigabe |
| **C** | Zur Leistungs-/Verhaltenskontrolle bestimmt | **Pflicht-Anhang Betriebsvereinbarung** |
| **D** | Notfall/sicherheitskritisch | Sofort-Freigabe + Nachgenehmigungs-Vorgang an GBR |

Bei **C**: Im Wizard erscheint ein Upload-Button für die unterzeichnete Betriebsvereinbarung. Submit ist gesperrt, solange kein Anhang da ist.

Bei **D**: Es muss von **Application Owner UND IT-Application-Owner** zusammen bestätigt werden (Vier-Augen-Prinzip). Begründung ist Pflicht.

### 1.4 Antrag einreichen

1. Wenn Pflichtfeld-Zähler bei „0" ist → Button **„Antrag einreichen"** wird aktiv
2. Klicken → Bestätigungsdialog
3. Status wechselt von `DRAFT` zu `IN_REVIEW` (bzw. `PROVISIONALLY_APPROVED` bei Kategorie D)
4. Alle relevanten Freigeber werden benachrichtigt (in der Demo: nur in der `notifications`-Tabelle protokolliert, kein echter E-Mail-Versand)

### 1.5 Auf Rückfragen reagieren

Wenn ein Reviewer einen Wert abgelehnt hat:

1. Status des Antrags ist `CHANGES_REQUESTED`
2. Im Dashboard erscheint die Karte **„Mit Rückfragen"**
3. Antrag öffnen — abgelehnte Felder sind **rot markiert**
4. Wert anpassen ODER im Kommentar-Thread des Felds antworten
5. Button **„Erneut zur Prüfung freigeben"** klicken
6. Nur die geänderten Felder gehen wieder in `IN_REVIEW`; bereits freigegebene Felder behalten ihren Status

---

## 2. Freigaben erteilen (Freigeber)

### 2.1 Offene Freigaben sehen

Im Dashboard erscheint die Tabelle **„Offene Freigaben"**:

- **Gelbe Markierung:** länger als 7 Tage offen (Reminder-Stufe 2)
- **Rote Markierung:** länger als 14 Tage offen (Reminder-Stufe 3 → Eskalation an Admin)

### 2.2 Antrag prüfen

1. Auf den Titel des Antrags klicken
2. Du siehst den Antrag in der **Reviewer-Ansicht**
3. Linke Sidebar zeigt alle Sektionen mit Anzahl der für **deine Rolle relevanten Felder**
4. Pro Feld:
   - **Wert** (read-only)
   - **Status-Dropdown** (nur bei F-Feldern für deine Rolle)
   - **Kommentar-Thread**

### 2.3 Status setzen

Pro Feld kannst du setzen:

| Status | Bedeutung | Kommentar |
|---|---|---|
| `IN_PROGRESS` | Default vor Bearbeitung | optional |
| `IN_REVIEW` | Du arbeitest gerade dran | optional |
| `APPROVED` | Du gibst frei | optional |
| `REJECTED` | Du lehnst ab | **Pflicht** |
| `ACKNOWLEDGED` | Nur bei Kategorie A für BR | optional |

**Wichtig:**
- Bei `REJECTED` MUSST du einen Kommentar hinterlegen — sonst wird der Klick ignoriert
- Sobald du `REJECTED` setzt, geht der gesamte Antrag in `CHANGES_REQUESTED`
- Sobald **alle F-Felder** mindestens eine `APPROVED`-Entscheidung haben, wird der Antrag final freigegeben (`APPROVED`) und automatisch ins Applikationsverzeichnis übernommen

### 2.4 Mehrfach-Mitgliedschaft

Mehrere Personen können in derselben Rolle sein (z. B. zwei BR-Mitglieder).
**Eine Freigabe pro Rolle reicht** (ODER-Verknüpfung). Wer schneller ist, gibt frei — die anderen sehen den Status weiterhin und können die Position des Kollegen kommentieren, müssen aber nicht erneut bestätigen.

### 2.5 Bulk-Aktion

Über der Sektionsliste: **„Alle nicht-relevanten Felder als gesehen markieren"**.
Setzt alle I-Felder, die deine Rolle nur informieren, automatisch auf `IN_REVIEW` (gesehen).

---

## 3. Administration (Admin)

### 3.1 Benutzerverwaltung

`/admin/users`

- Alle Benutzer als Tabelle, mit Rollenzuordnung
- Neuer Benutzer: Modal-Dialog mit E-Mail, Name, initialem Passwort, Rollenauswahl (Multi-Select)
- Benutzer deaktivieren (Soft-Delete, hält Audit-Historie)

### 3.2 Audit-Log

`/admin/audit`

- Append-only Log aller sicherheitsrelevanten Aktionen
- Filter: Aktion, Akteur, Zeitraum
- Aktionen u. a.: `LOGIN`, `LOGOUT`, `FIELD_UPDATED`, `DECISION_SET`, `REQUEST_SUBMITTED`, `REQUEST_APPROVED`, `REMINDER_SENT`, `ATTACHMENT_UPLOADED`

### 3.3 Reminder-Engine

Automatisch täglich (`scheduler.py` via APScheduler) — jeder offene Antrag wird geprüft:

| Tage offen | Stufe | Empfänger |
|---|---|---|
| 3 | 1 | alle Mitglieder der zuständigen Rolle |
| 7 | 2 | + Antragsteller, ggf. Vorgesetzte |
| 14 | 3 | + Admin (Eskalation) |

Manueller Trigger im Dashboard: **„Reminder-Scan jetzt ausführen"** — nützlich für Demos.

### 3.4 Applikationsverzeichnis

`/catalog`

- Alle final freigegebenen Anwendungen + per Bestandsimport eingetragene
- Suche, Filter nach Status / Quelle (FROM_REQUEST oder IMPORTED)
- **CSV-Export** (`/catalog/export.csv`)
- **Bestand importieren** (Admin): manueller Eintrag ohne den vollen Workflow

### 3.5 Datensicherung

Demo-Datenbank: `/opt/sysintro/data/sysintro.db`. Empfohlen:

```bash
sudo -u sysintro sqlite3 /opt/sysintro/data/sysintro.db ".backup /opt/sysintro/data/sysintro-$(date +%F).db.bak"
```

Anhänge: `/opt/sysintro/attachments/<request_id>/<uuid>.<ext>` — beim Backup mitsichern.

---

## 4. Häufige Fragen

**F: Kann ich einen eingereichten Antrag zurückziehen?**
Nicht als Antragsteller (Demo-Beschränkung). Admin kann via DB-Eingriff oder UI-Knopf zurückziehen — wird dann revisioniert.

**F: Was passiert beim Wechsel der Systemkategorie nach Submit?**
Alle BR-Approvals werden zurückgesetzt — der Antrag durchläuft den BR-Pfad neu.

**F: Was, wenn niemand aus einer Rolle reagiert?**
Stufe 3 nach 14 Tagen → Admin wird eskaliert. Rollen sollten daher Verteilerlisten haben (`Role.notification_email`).

**F: Sehe ich, wer was geändert hat?**
Ja — pro Feld gibt es eine **Revisionsansicht** (Zeitstrahl + Diff-Viewer). Zusätzlich das Audit-Log.
