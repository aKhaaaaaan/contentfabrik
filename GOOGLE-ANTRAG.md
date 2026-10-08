# YouTube-API-Prüfantrag (Audit) – fertige Antworten (Stand 03.10.2026)

**Nachtrag 08.10.2026 (Claude):** Google (youtube-disputes, Mail 08.10. 01:21)
verlangte binnen 7 Werktagen (1) Upload-Skript/Screencast auf Englisch mit
Endergebnis und (2) ausgewerteten Beispielbericht der API-Daten. Beantwortet
am 08.10. 08:11 aus [privates Google-Konto] an youtube-disputes + savehours24 mit
[antrag/Contentfabrik_YouTube_API_Review.pdf](antrag/Contentfabrik_YouTube_API_Review.pdf):
echter privater API-Upload auf AI Tools Explained (Video 5xBDlGZWbys, privat,
verarbeitet, 1:23) plus Analysebericht aus den am 08.10. abgerufenen Zahlen.
Lokaler OAuth-Zugang fuer Business Origin Stories ist abgelaufen (Token-Refresh
HTTP 400) - neu anmelden (`fabrik/anmelden.py`), bevor Business-Uploads/Analytics
ueber diesen Zugang laufen. Das Testvideo kann nach der Pruefung geloescht werden.

**Einordnung 05.10.2026:** Dieses Dokument protokolliert den am 04.10.
eingereichten Antrag. Geplanter Upload (`publishAt`), Editieren/Stornieren
und die Diagramme sind teilweise Zielarchitektur. Der aktive Tageslauf
sendet Vorschauen zum manuellen Upload. Eine automatische Veroeffentlichung
wird erst nach ausdruecklich gespeicherter Freigabe angebunden; siehe
[README.md](README.md). Eine Audit-Zusage ist im Projekt nicht dokumentiert.

Google dokumentiert aktuell getrennte Kontingente fuer `videos.insert`
und `search.list` (je 100 Aufrufe/Tag), neben 10.000 Einheiten fuer andere
Methoden. Die unten eingereichten 1.600 Einheiten je Upload beschreiben den
damaligen Antrag, keine aktuelle Verbrauchsrechnung.
[Primaerquelle, abgerufen 05.10.2026](https://developers.google.com/youtube/v3/determine_quota_cost).

**Warum:** Ohne Prüfung bleibt jedes per API hochgeladene Video für immer privat
(Google-Doku videos.insert). Nach der Prüfung lädt das Tool selbst hoch und
veröffentlicht zur geplanten Zeit – du musst nichts mehr von Hand machen.

**Formular:** https://support.google.com/youtube/contact/yt_api_form
(angemeldet als das Google-Konto, dem das Cloud-Projekt gehört: [privates Google-Konto])

**Dauer:** Google nennt keine Frist; Berichte sprechen von mehreren Wochen.

## Vor dem Absenden von dir zu klären (nur du kannst das)
1. **Dein vollständiger rechtsgültiger Name** (Abschnitt 2).
2. **Ist Savehours24 ein angemeldetes Gewerbe?** Wenn ja → „als Organisation“, Name „Savehours24“.
   Wenn nein → „als Einzelnutzer*in“ und bei Organisation „im eigenen Namen“ (so verlangt es das Formular).
3. Die Bestätigungen in Abschnitt 7 liest und setzt du selbst.

## Abschnitt 1 – Art des Antrags
- **Compliance-Audit durchführen, um zusätzliches Kontingent anzufordern**
  (in Abschnitt 5 dann „Keine Änderung / Standardkontingent“ – wir brauchen nur die Prüfung, kein Mehr-Kontingent)

## Abschnitt 2 – Organisation und Kontakt
- Antrag: siehe Punkt 2 oben
- Website: `https://contentfabrik.pages.dev`
- Land: Deutschland · Adresse: [Anschrift entfernt] · Stadt: [Ort entfernt] · Bundesland: Hessen · PLZ: [entfernt]
- Kategorie: **Medien und Unterhaltung**
- Größe/Art: **Entwickler*in (unabhängig) / Alleininhaber*in**
- Primärer Kontakt: dein Name · `[Kontakt-E-Mail, privat]`
- Technischer und geschäftlicher Kontakt: „Entspricht dem primären Kontakt“ anhaken

## Abschnitt 3 – Geschäftsmodell
**Beschreibe die Arbeit deiner Organisation in Verbindung mit YouTube:**
```
Savehours24 runs two educational YouTube channels with short videos: "AI Tools Explained" (free and open-source AI tools and models) and "Business Origin Stories" (how well-known companies started). Contentfabrik is our internal tool that produces these videos from public sources (Wikipedia, Wikimedia Commons, GitHub, Hugging Face), fact-checks every script, scores the story (hook, tension, ending) and rewrites it until it reaches our quality target, reviews the finished video the same way, and uploads the finished video to our own channels with a scheduled publish time. Every video is labeled as altered/synthetic content because it uses an AI voice. Before release, the operator receives a preview on a private Telegram chat and can edit or cancel the video. Once a day the tool reads the statistics of our own videos (YouTube Analytics) to learn which topics and formats viewers like, so the next videos get better. The tool is used only by its operator, on our own two channels. It has no other users, is not sold, does not access other channels' private data and does not collect any viewer data.
```
- Zielgruppe: **Interne Nutzer*innen**
- Monetarisierung: **Kostenloser Dienst (wir berechnen für die Nutzung keine Gebühren)**
- Werbung auf/in YouTube-Inhalten: **Nicht zutreffend**
- Google-Ansprechpartner: **Nein**
- Wie von der API erfahren: **Google-Entwicklerdokumentation**
- Verknüpfte Kanäle:
  `https://www.youtube.com/channel/UCNDiRDF5DHCkpQxbeqBvz7A` und
  `https://www.youtube.com/@BusinessOriginStoriesTV`
- Rechteinhaber-ID, Google Ads: leer lassen

## Abschnitt 4 – API-Client
- Name: **Contentfabrik** · enthält „YouTube“: **Nein**
- Primäre Zugriffs-URL: `https://contentfabrik.pages.dev`
- Datenschutz: `https://contentfabrik.pages.dev/privacy`
- Nutzungsbedingungen: `https://contentfabrik.pages.dev/terms`
- Öffentlich zugänglich: **Nein**
- Demokonto: **keins** – nie ein Passwort eintragen. Bei „Besondere Hinweise für den Zugriff“:
```
Internal tool without a user interface or login. It runs as a scheduled job (GitHub Actions) for the operator only. Architecture and user flow are attached in section 6. We are happy to provide a screen recording of an upload on request.
```
- Die Bestätigung zum Demokonto anhaken (sonst lässt das Formular nicht weiter).

## Abschnitt 5 – Anwendungsfälle
- Anzahl Projekte: **1** · Projektnummer: **315902188074** (Projekt-ID contentfabrik-510416, geprüft in der Cloud Console)
- Kategorien: **Video-Upload und Kontoverwaltung**, **Internes Unternehmenstool**, **Analysen und Berichte**
- OAuth-Anmeldung: **Ja**
- Verwendete Methoden (in der Liste anhaken):
  `youtube.videos.insert`, `youtube.videos.update`, `youtube.videos.list`,
  `youtube.channels.list`, `youtube.playlistItems.list`, `youtube.search.list`
  und YouTube Analytics `reports.query`
- Abschnitt „abgeleitete Messwerte“: **nicht ausfüllen** (brauchen wir nicht)
- Kontingent: **Keine Änderung / Standardkontingent (10.000)**

## Abschnitt 6 – Nachweise
- Architekturdiagramm + Nutzerfluss: `antrag/contentfabrik-architektur-ablauf.pdf`
  (2 Seiten, 1600×900, 236 KB – unter der 10-MB-Grenze; PDF ist erlaubt)

## Abschnitt 7
- Alle Bestätigungen selbst lesen und anhaken, dann **Senden**.

## Was schon vorbereitet ist (geprüft 03.10.2026)
- Datenschutzerklärung erfüllt III.A.2 der Entwicklerrichtlinien (YouTube-AGB, Google-Datenschutz,
  Widerrufslink, Cookies/Gerätedaten/Inhalte Dritter, Kontakt).
- Widerruf: Der tägliche Abruf löscht die gespeicherten Zahlen eines Kanals automatisch, wenn der
  Zugang widerrufen wurde (III.E.4) – getestet.
- Jedes Video wird als KI-Inhalt gekennzeichnet (containsSyntheticMedia).

## Nach der Freigabe zu bauen
- Upload mit `publishAt` (geplante Veröffentlichung 15:00 New York) statt Telegram-Hand-Upload;
  Telegram-Vorschau mit Stopp-Möglichkeit bis dahin. Erst bauen, wenn Google zugestimmt hat –
  so steht es auch im Antrag.

## ABGESCHICKT am 04.10.2026 (Bestaetigung: „Ihre E-Mail wurde gesendet")
- Als Einzelperson ([Name, privat]), Projekt „Savehours24", Kontakt [Kontakt-E-Mail, privat].
- Zusaetzlich verlangt und eingereicht: Nachweise je Projekt (antrag/datenschutz.png, startseite.png,
  nutzungsbedingungen.png, oauth-ablauf-und-widerruf.pdf) und Kontingentangaben fuer search.list
  (1.000 Einheiten/Tag) und videos.insert (3.200 Einheiten/Tag = 2 Uploads), Rest Standardkontingent.
- Startseite bekam dafuer den Hinweis „Uses YouTube API Services" mit Links zu YouTube-AGB,
  Google-Datenschutz und unserer Datenschutzerklaerung (Google verlangt sichtbares YouTube-Branding).
- Antwort kommt per E-Mail an [Kontakt-E-Mail, privat]; Google nennt keine Frist.
