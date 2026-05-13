# Frageliste Systemeinführung – SysIntro (Final-State mit Postgres + Keycloak)

Antworten für Spalte H zur direkten Übernahme. Reihenfolge entspricht der Excel-Datei
(Zeile 2 = Antragsteller-Name … Zeile 52 = Sonstiges).

| Zeile | Nr. | Kategorie | Frage | Antwort (Spalte H) |
|---|---|---|---|---|
| 2  | 1.1   | Antragsteller  | Name                                 | Daniel Hufnagel |
| 3  | 1.2   | Antragsteller  | Email                                | daniel.hufnagel@amedes-group.com |
| 4  | 1.3   | Antragsteller  | Abteilung                            | IT Application Management |
| 5  | 2.1   | Produkt        | Hersteller                           | amedes (Eigenentwicklung) |
| 6  | 2.1   | Produkt        | Name                                 | SysIntro |
| 7  | 2.2   | Produkt        | Version                              | 1.0 |
| 8  | 2.3   | Produkt        | Beschreibung des Systems             | Web-Plattform zur digitalen Erfassung & Freigabe von Software-Einführungsanträgen; ersetzt Excel/E-Mail durch pro-Feld-Rollenfreigabe mit Audit-Trail. |
| 9  | 3.1   | Projekt        | Einführungszeitpunkt                 | Q3 2026 (POC seit Q1 2026 produktiv) |
| 10 | 3.2   | Projekt        | Standort                             | Zentrale Web-Anwendung im amedes-RZ Frankfurt; alle amedes-Standorte greifen über Browser zu (HTTPS). |
| 11 | 03.03 | Projekt        | Softwareauswahl                      | Nein. Marktanalyse ergab kein Produkt mit pro-Feld-Rollenfreigabe + Audit-Trail; daher Eigenentwicklung amedes IT. |
| 12 | 04.01 | Datenschutz    | Personenbezogene Daten               | Ja. Name, dienstliche E-Mail und Rolle der Antragsteller/Reviewer (Quelle: Keycloak, JIT-Sync). |
| 13 | 04.02 | Datenschutz    | Verantwortlicher Bereich (fachlich)  | IT Application Management (Leitung). Stellvertretung gemäß amedes-Vertretungsplan. |
| 14 | 04.03 | Datenschutz    | Anwendung des Systems                | Erfassung & Freigabe-Workflow für neu einzuführende Software. Bisher Excel + E-Mail-Abstimmung → künftig zentrale Plattform mit pro-Feld-Reviews, Statusmaschine und Audit-Trail. |
| 15 | 04.04 | Datenschutz    | Anwender des Systems                 | ca. 30 Reviewer (Betriebsrat, IT-Security, Datenschutz, App-Manager, App-Betrieb, Lizenzen) + bis zu 200 Antragsteller aus der amedes-Gruppe. Admins: 3 (IT Application Management). |
| 16 | 04.05 | Datenschutz    | Betroffene Personen                  | Mitarbeiter (Antragsteller, Reviewer, Application Owner). Keine Patientendaten, keine externen Personen. |
| 17 | 04.06 | Datenschutz    | Auswirkungen auf Mitarbeiter         | Digitale, transparente Antragsstellung; weniger Excel/E-Mail; vollständige Nachvollziehbarkeit aller Entscheidungen; Reviewer sehen präzise ihre Zuständigkeit. |
| 18 | 04.07 | Datenschutz    | Rechtemanagement                     | Ja. Rollenbasierte Zugriffsrechte (RBAC) über Keycloak Realm-Rollen, in SysIntro auf REQUESTER/BR/IT_SECURITY/DATA_PROTECTION/APP_MANAGER/APP_OPERATION/LICENSE_MGMT/ADMIN gemappt. JIT-Sync, kein lokales Passwort. |
| 19 | 04.07 | Datenschutz    | Schulungsplan                        | Inline-Hilfetexte je Feld in der Anwendung; ca. 30 Min. Onboarding-Session pro Reviewer-Rolle vor Go-Live. Benutzerhandbuch im amedes-Wiki. |
| 20 | 04.08 | Datenschutz    | Werden Mitarbeiterdaten gespeichert? | Ja |
| 21 | 04.09 | Datenschutz    | Eignung Leistungsüberwachung         | Nein. Audit-Log dokumentiert ausschließlich Antrags- und Freigabe-Ereignisse, keine Verhaltens- oder Leistungsdaten der Mitarbeiter. Zugriff auf Audit-Log nur für ADMIN-Rolle. |
| 22 | 04.11 | Datenschutz    | Zweck Mitarbeiterdaten               | Identifikation des Antragstellers, Zuordnung der Reviewer-Verantwortlichkeit, Nachvollziehbarkeit von Freigabe-Entscheidungen. |
| 23 | 04.13 | Datenschutz    | Löschfristen Mitarbeiterdaten        | Antragsdaten: 10 Jahre nach Abschluss (Aufbewahrungspflicht IT-Akten). User-Stammdaten: aus Keycloak (JIT) — Lebenszyklus folgt amedes-IdM beim Austritt. |
| 24 | 05.01 | Schnittstellen | Umsysteme und Daten                  | Keycloak (OIDC, Authentifizierung + Rollen). SMTP-Relay (Benachrichtigungs-Mails an Antragsteller/Reviewer). Datenbank PostgreSQL ist intern, keine externe Schnittstelle. |
| 25 | 05.02 | Schnittstellen | Periodizität                         | Echtzeit (OIDC bei Login, SMTP bei Workflow-Trigger). |
| 26 | 05.03 | Schnittstellen | Intervalle                           | n. a. (ausschließlich Echtzeit, keine periodischen Schnittstellen) |
| 27 | 06.01 | Datenschutz    | Verarbeitungstätigkeit               | Verwaltung von Software-Einführungsanträgen der amedes-Gruppe |
| 28 | 06.02 | Datenschutz    | Rechtsgrundlage                      | Art. 6 Abs. 1 lit. f DSGVO — berechtigtes Interesse an einem geordneten, auditierbaren IT-Einführungsprozess inkl. BR-Beteiligung. |
| 29 | 06.03 | Datenschutz    | Personenkategorien                   | Mitarbeiter (Antragsteller, Reviewer, Application Owner). |
| 30 | 06.04 | Datenschutz    | Datenkategorien                      | Name, dienstliche E-Mail, Rolle/Abteilung, Antragsinhalte, Freigabe-Entscheidungen je Rolle mit Zeitstempel. |
| 31 | 06.05 | Datenschutz    | Empfängerkategorien                  | Keine externen Empfänger. Intern: jeweilige Reviewer-Rollen je nach Feld-Zuständigkeit (BR, IT-Sec, DSB, AppMgr, Ops, Lic). |
| 32 | 06.06 | Datenschutz    | Datenübermittlung Drittländer        | Nein. Hosting ausschließlich in EU (PostgreSQL und Anwendung im amedes-Rechenzentrum Frankfurt). Keycloak ebenfalls amedes-intern. |
| 33 | 06.07 | Datenschutz    | Löschfristen Datenkategorien         | Antragsdaten + Audit-Log: 10 Jahre nach Abschluss (append-only). Attachments: mit Antrag. User-Stammdaten: aus Keycloak (JIT), kein separater Lebenszyklus in SysIntro. |
| 34 | 07.02 | Lizenzen       | Lizenzbedarf                         | Keine. Eigenentwicklung amedes. Eingesetzte Open-Source-Komponenten (FastAPI, PostgreSQL, Keycloak, nginx) unter freien Lizenzen (BSD/MIT/PostgreSQL/Apache 2.0). |
| 35 | 08.01 | Betrieb        | Herstellersupport                    | n. a. Eigenentwicklung. Wartung & Weiterentwicklung durch amedes IT Application Management. OSS-Komponenten via aktive Community-Support-Kanäle. |
| 36 | 08.02 | Betrieb        | amedes IT Support                    | Ja. amedes IT Application Management (1st & 2nd Level Support) über Ticket-System. |
| 37 | 08.03 | Betrieb        | amedes IT Betrieb                    | Vollumfänglich: Patching, Monitoring, tägliches Backup (pg_dump), Release-Deployments, PostgreSQL-DBA, TLS-Zertifikate, Logs. Alles durch amedes IT. |
| 38 | 09.01 | Cloud          | Cloudbasiertes System                | Nein. On-Prem im amedes-Rechenzentrum Frankfurt. Vorgelagert: nginx + Cloudflare nur als TLS-/DDoS-Schicht ohne Datenhaltung. |
| 39 | 09.02 | Cloud          | Welche Cloud                         | n. a. (On-Prem amedes-RZ Frankfurt) |
| 40 | 09.02 | Cloud          | Exitstrategie                        | n. a. (On-Prem). Datenexport jederzeit via pg_dump (SQL) oder JSON-Export der Anträge möglich. |
| 41 | 09.03 | Cloud          | Anmeldedaten/Speicherung             | n. a. SSO über amedes-Keycloak (kein lokales Passwort in SysIntro). Anwendungs-Secrets im amedes-Vault. |
| 42 | 10.01 | SLA            | Betriebszeiten                       | Mo–Fr 7:00–19:00 Uhr; Wartungsfenster So 02:00–06:00 Uhr. |
| 43 | 10.02 | SLA            | Supportzeiten                        | Mo–Fr 8:00–17:00 Uhr durch amedes IT Application Management. |
| 44 | 10.03 | SLA            | Reaktionszeiten                      | 4 Stunden innerhalb des Supportzeitraums. |
| 45 | 10.04 | SLA            | Herstellervereinbarungen             | n. a. (Eigenentwicklung, keine externen SLA). OSS-Komponenten ohne Hersteller-SLA. |
| 46 | 10.04 | SLA            | Lösungszeiten                        | 16 Stunden innerhalb des Supportzeitraums. |
| 47 | 10.05 | SLA            | Recovery Time Objective              | 4 Stunden. |
| 48 | 10.06 | SLA            | Recovery Point Objective             | 24 Stunden (täglicher pg_dump nach S3 + WAL-Archivierung für Point-in-Time-Recovery). |
| 49 | 10.07 | SLA            | Aufbewahrungszeiten (nicht pb)       | Anträge + Audit-Log: 10 Jahre. Attachments (BV, Verträge): mit dem Antrag. Stammdaten (Rollen, Vendoren): unbefristet. |
| 50 | 11.01 | Kosten         | Einmalkosten / Investitionskosten    | CAPEX: gering. Interne Entwicklungsaufwände im laufenden IT-Budget enthalten (keine externen Lizenz- oder Hardware-Kosten). |
| 51 | 11.02 | Kosten         | Betriebskosten                       | OPEX: Hosting (amedes-RZ), Backup (S3), Keycloak-Anteil und Wartung im laufenden IT-Budget enthalten. |
| 52 | 12.01 | Sonstiges      | Sonstige Anmerkungen                 | Eigenentwicklung amedes IT Application Management. POC seit Q1 2026 produktiv. Vollständiger Go-Live Q3 2026 (Keycloak-Anbindung + PostgreSQL-Migration in Vorbereitung, siehe docs/GOLIVE.md). |
