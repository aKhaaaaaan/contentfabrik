# Contentfabrik – Konzept

Stand 02.10.2026 · Arbeitstitel „Contentfabrik" · ein Tool für zwei Ziele

## Aktuelle Einordnung – 05.10.2026

Dieses Dokument enthaelt den Gesamtplan und historische Messungen. Den
heutigen Betriebsstand beschreibt [README.md](README.md). Massgeblich:

- Aktiv sind zwei englische Kanaele, Kurzvideos und Telegram-Vorschauen.
  Ein optionaler Langformat-Pilot mit eigener Dramaturgie/Querformat ist im
  Code vorbereitet, noch nicht mit echten Modellen gerendert. Dashboard,
  Freigabe-Knoepfe und mehrere automatische
  Plattform-Uploads sind geplant, noch nicht durchgaengig umgesetzt.
- Vorschauen gibt es nur mit bestandenem Faktencheck, bestandener Technik
  und Skript-/Video-Note **mindestens 9/10**, jede Kategorie mindestens 8,
  ohne mittlere/schwere offene Probleme. Ausgefallene Pruefungen bestehen nicht.
  Ziel bleibt 10/10; das Tagesbudget gilt ueber alle Ersatzfenster hinweg.
- Gezielte Korrekturen desselben Videos und gemessenes Lern-Gedaechtnis sind
  jetzt umgesetzt: einzelne Eingriffsarten testen, bessere Fassungen behalten,
  bewaehrte Darstellungsprofile uebernehmen. Echte Video-/Cloud-Validierung
  steht noch aus; Ablauf und Grenzen sind in README.md dokumentiert.
- Der aktive Ablauf veroeffentlicht nichts automatisch. Auch spaeter darf
  eine geplante Veroeffentlichung erst nach gespeicherter Freigabe erfolgen.
- 0 EUR ist das Kostenziel innerhalb vorhandener Freikontingente. Pilotzeiten
  ohne heutige Story-/Video-Pruefungen sind keine Kapazitaetsgarantie;
  Einrichtung, Wiederholungen, Speicher und Auswertungen mitzaehlen.
- RPM-/CPM-Tabellen und behauptete virale Erfolgsformeln unten sind
  **Planungsannahmen aus Drittquellen**, keine eigenen gemessenen Einnahmen
  und keine garantierten Ergebnisse. CPM und RPM sind nicht austauschbar.
- TikTok Direct Post schliesst reine private Upload-Werkzeuge als
  Anwendungsfall aus. Der aktuelle App-Entwurf hat deshalb ein konkretes
  Pruefhindernis; manuelles Hochladen bleibt der aktive Weg.
  [Offizielle TikTok-Richtlinie](https://developers.tiktok.com/docs/en/content-sharing-guidelines).
- Die YPP-Aenderung zum 01.02.2027 ist inzwischen offiziell bestaetigt
  (siehe 2d); bisherige Upload-Kontingentrechnungen im Antrag sind Historie.
  [Offizielle YouTube-Kontingente](https://developers.google.com/youtube/v3/determine_quota_cost).

Die folgenden Abschnitte bleiben als Konzept und Entscheidungsprotokoll
erhalten. Widersprueche zum heutigen Stand sind nach der Einordnung oben
und dem Code zu lesen.

> Grundsatz: Was hier steht, ist geprüft (Quellen am Ende) oder ausdrücklich
> als **ungeprüft** markiert. Ungeprüftes wird im Pilot gemessen, nicht
> angenommen.

---

## 1. Ziel

Ein Tool, das **jeden Tag von selbst** Themen findet, Skripte schreibt,
Videos/Beiträge erstellt und hochlädt – **erst nach deiner Freigabe**, die du
mit einem Tipp auf dem Handy gibst. Online von überall erreichbar, ohne dass
ein PC laufen muss. Fixkosten: **0 €**.

Zwei Säulen, **ein** Tool (gleicher Ablauf, verschiedene Kanäle):

| Säule | Ziel | Sprache | Plattformen |
|---|---|---|---|
| **A – Einnahmen** | Werbegeld + Affiliate | Englisch / ohne Sprache | YouTube, TikTok, Instagram, Facebook |
| **B – Kunden** | warme Leads für BusinessAssistant24, Sortidoc, neue Tools | Deutsch | LinkedIn, YouTube, Instagram, Facebook |

---

## 2. Nischen – nach Daten, nicht nach Gefühl

**Ungepruefte Planungswerte aus Drittquellen (RPM/CPM), keine Einnahmezusage:**

| Nische | RPM (lange Videos) | Bemerkung |
|---|---|---|
| B2B-Software / SaaS-Reviews | 18–38 $ | höchste; dazu Affiliate-Provisionen |
| Persönliche Finanzen / Investieren | 15–40 $ | sehr hoch, aber heikel: Fehlinformation = Risiko |
| KI-Tools / Tech-Tutorials | 15–30 $ | wächst am schnellsten 2026 |
| Business-Ursprungsgeschichten | 8–18 $ | Dokumentarstil, gut faceless |
| Psychologie | 8–12 $ | |
| Schlaf / Entspannung (ohne Sprache) | CPM 5–15 $, lange Wiedergabe | hohes Sperr-Risiko bei Gleichförmigkeit |
| Lofi / Ambient-Musik (ohne Sprache) | 1–4 $ | Geld eher über Spotify, Lizenzen |

**Shorts zahlen kaum:** 0,05–0,30 $ je 1.000 Aufrufe. Shorts sind
**Werbung für die langen Videos**, nicht die Einnahmequelle.

**Empfehlung Start Säule A (2 Kanäle, nach 60 Tagen auswerten):**
1. **„AI Tools Explained" (Englisch)** – hohe RPM, Affiliate (KI-Tools zahlen
   Provisionen), und es passt zu deinen eigenen Apps. Format: 1 langes Video
   pro Woche + täglich 1 Short daraus.
2. **„Business Origin Stories" (Englisch)** – gute RPM, Geschichten
   funktionieren faceless und sind von Natur aus abwechslungsreich (wichtig
   für YouTubes Regel, Abschnitt 4).

**Bewusst NICHT zum Start:** Finanzen (Fehler bei Geldthemen sind heikel –
später, wenn die Pipeline sitzt), reine Schlaf-/Ambient-Kanäle ohne Sprache
(gerade diese Massenware sperrt YouTube 2026; nur mit echter Abwechslung,
später als Test).

**Säule B (Deutsch):** Themen aus dem Alltag der Zielkunden – Handwerk,
Dienstleister, Praxen: „Rechnungen ohne Tipparbeit", „Mahnwesen
automatisch", „Belege per Foto ablegen", „GoBD in 60 Sekunden". Jeder Beitrag
endet mit einem Angebot (Testzugang / Demo), das Kontakte einsammelt.

---

## 2a. Ergänzungen nach Prüfung eines Vorschlags einer anderen KI (02.10.2026)

**Übernommen:**
- **Auswahlformel für Nischen:** RPM × Bindung (Retention) × Kaufabsicht –
  nicht nach Aufrufen allein. Gilt für jede neue Kanal-Entscheidung.
- **Weitere Kandidaten-Nischen** (Geschichten = lange Bindung, faceless):
  „Betrayal/Revenge Stories" (ca. 12–13 $ RPM, stark wachsend) und
  „Legal/Court Drama" (12–18 $ CPM). **Nur eigene, neu geschriebene
  Geschichten** – kein Übernehmen fremder Texte (Urheberrecht, YouTube-Regel).
- **Einnahmen nicht nur Werbung:** Affiliate-Links (Software-Anbieter zahlen
  teils hohe Provisionen je Anmeldung), eigene digitale Produkte, später
  TikTok Shop. Gehört bei jedem Kanal zur Planung.
- **Kostenlose KI für Skripte:** Gemini (z. B. Flash: 1.500 Anfragen/Tag frei)
  und Groq (14.400 Anfragen/Tag frei, gewerblich erlaubt). Damit können auch
  die Skripte 0 € kosten; der OpenAI-Schlüssel bleibt für die Qualitätsprüfung.
- **Rückfallebene Hochladen:** Dienste wie Blotato (ab 29 $/Monat) oder Zernio
  haben die Plattform-Prüfungen schon und veröffentlichen sofort öffentlich.
  **Nur falls** unsere eigenen Prüfungen bei YouTube/TikTok scheitern – und nur
  nach Rückfrage, weil es Geld kostet.

**Nicht übernommen – und warum:**
- **edge-tts:** nutzt einen inoffiziellen Microsoft-Zugang (Grauzone, kann
  jederzeit abgeschaltet werden). Kokoro ist frei lizenziert und besser bewertet.
- **ElevenLabs, KI-Video (Kling, Runway, Luma), Ayrshare (ab 149 $/Monat):**
  kostenpflichtig – widerspricht 0 € zum Start.
- **n8n:** braucht einen dauerhaft laufenden Server oder ein Abo.
- **Repo „video-autopilot":** gute Ideen (9 Stufen, Wiederholungsgedächtnis),
  aber **keine Lizenz sichtbar** – darf also nicht übernommen werden, schon gar
  nicht für ein späteres Verkaufsprodukt; lädt außerdem über das kostenpflichtige
  Ayrshare hoch. Nur als Ideengeber.
- **„700.000 $/Jahr bei 2 Stunden täglich":** Einzelanekdote, nicht prüfbar.
  „Radikale Standardisierung und tägliche Uploads" ist seit 2026 genau das, was
  YouTube als Massenware sperrt.
- **RPM KI-Tools:** die andere KI nennt 7–15 $, unsere Quellen 15–30 $ – die
  Quellen weichen ab; maßgeblich werden unsere eigenen Zahlen im Dashboard.

Quellen: [video-autopilot](https://github.com/aredwan-xyz/video-autopilot), [Gemini Free Tier](https://www.memetik.ai/guides/gemini-api-free-tier-limits), [Groq Free Tier](https://tokenmix.ai/blog/groq-free-tier-limits-2026), [Ayrshare-Preise](https://www.upload-post.com/ayrshare-pricing/), [Blotato-Preise](https://aifunnelinsider.com/blotato-review/), [Zernio – ohne eigene App-Prüfung](https://zernio.com/blog/social-media-posting-api)

---

## 2b. Ergänzungen nach Prüfung eines YouTube-Videos („Ranking-Shorts", 02.10.2026)

**Übernommen:**
- **Vorbild-Analyse als Funktion:** Das Tool beobachtet erfolgreiche Kanäle
  der Nische über die YouTube-Schnittstelle (öffentliche Zahlen, kostenlos)
  und findet **Ausreißer-Videos** (weit über dem Kanal-Durchschnitt). Deren
  Themen werden zu Ideen für uns – mit eigenem Inhalt, nicht kopiert.
- **Ranking-Format** (funktioniert nachweislich) – **mit eigenem Material**:
  „Top 6 KI-Tools für …", „Die 6 größten Firmenpleiten", „6 Gerichtsurteile,
  die …". Regeln aus dem Video: **5–7 Plätze**, Reihenfolge **gemischt** (nicht
  7-6-5-…), **Platz 1 immer zuletzt** – das hält Zuschauer bis zum Ende.
- **Titel im Bild:** genau **zwei Zeilen**, die Schlüsselwörter **farbig**
  hervorgehoben – Teil der Stilvorlage je Kanal.
- **Beständigkeit:** täglich veröffentlichen, kein Tag Pause – passt zu
  unserem Takt (1 Short/Tag je Kanal), aber jedes Video mit eigenem Wert.
- **Nur auf bewährte Themen setzen:** Ideen aus Themen, die schon viral liefen,
  statt aus dem Bauch.

**Nicht übernommen – und warum:**
- **Fremde TikTok-/Instagram-Clips herunterladen und zusammenschneiden:**
  1. Urheberrecht – die Clips gehören anderen; Folge: Content-ID-Ansprüche,
     Verwarnungen, Kanal-Sperre.
  2. YouTubes Regel „reused content": Zusammenschnitte ohne nennenswerten
     eigenen Beitrag werden nicht bezahlt; 2026 prüft YouTube ausdrücklich,
     ob ein anderer dasselbe Video aus denselben Clips nachbauen könnte –
     genau das trifft hier zu.
  3. TikTok untersagt das Herunterladen fremder Inhalte zur Weiterverwendung.
- **„Rank Real"**: im Video beworbenes Werkzeug mit Empfehlungs-Link – nicht
  nötig, das Ranking-Format baut unser Video-Bauer selbst.
- **Einnahme-Schätzungen von VidIQ als Beleg**: Schätzungen, keine echten
  Zahlen; die vorgezeigten Kanäle sind ausgewählte Ausreißer.
- **„In wenigen Wochen monetarisiert"**: nicht belegt (Abschnitt 9).
- **Shorts-RPM „0,40 $ in den USA"**: andere Quellen nennen 0,05–0,30 $ –
  maßgeblich werden unsere eigenen Zahlen.

Quellen: [vidIQ – Reused Content Policy](https://vidiq.com/blog/post/youtube-reused-content-policy-guide/), [YouTube-Hilfe – Monetarisierungsrichtlinien](https://support.google.com/youtube/answer/1311392?hl=en), [veefly – Reused Content 2026](https://blog.veefly.com/guide/youtube-reused-content/)

---

## 2c. Rechte-Regeln und dritte Einnahmequelle „Clipping" (02.10.2026)

**Was erlaubt ist – fest im Tool verankert:**
| Weg | erlaubt? | Bedingung |
|---|---|---|
| Thema, Idee, Fakten, Aufbau eines viralen Videos übernehmen | **ja** | eigenes Skript in eigenen Worten, eigene Bilder |
| Transkript eines fremden Videos **wörtlich** vorlesen lassen | nein | Text ist geschützt |
| Fremde Videos schneiden, überlagern, mit Effekten/Kommentar versehen | **nein**, ohne Zustimmung | § 23 UrhG: Bearbeitungen brauchen die Zustimmung; nur bei „hinreichendem Abstand" (Original verblasst) nicht |
| Material aus **offiziellen Clipping-Kampagnen** (z. B. MrBeasts „Vyro") | **ja** | Vorgaben der jeweiligen Kampagne einhalten, Kampagne im Tool dokumentieren |
| Freie Stock-Clips (Pexels, Pixabay), eigene KI-Bilder | **ja** | Lizenz je Clip speichern |

Das Tool prüft vor jeder Freigabe: Ist jede Quelle eines Videos dokumentiert
(eigen / Stock mit Lizenz / Kampagne mit Erlaubnis)? Sonst keine Vorlage.

**Dritte Einnahmequelle – Clipping mit Erlaubnis:** Creator und Marken zahlen
über Plattformen wie **Vyro** (MrBeast, seit Okt. 2025) für Clips aus ihrem
freigegebenen Material, z. B. **3 $ je 1.000 Aufrufe**. Das Tool kann aus dem
freigegebenen Material Clips schneiden, untertiteln und auf eigenen Konten
posten – zusätzlich zu den eigenen Kanälen. **Vor Start:** Bedingungen der
konkreten Kampagnen prüfen (Plattformen, Kennzeichnung, Auszahlung).

Quellen: [§ 23 UrhG (dejure)](https://dejure.org/gesetze/UrhG/23.html), [Ratgeber Recht – Compilations](https://www.ratgeberrecht.eu/aktuell/compilations-und-urheberrecht/), [Tubefilter – Vyro](https://www.tubefilter.com/2025/10/14/mrbeast-vyro-clipping-platform-viewstats-expansion/), [Vyro-Review 2026](https://www.ssemble.com/blog/vyro-review-2026)

---

## 2d. Plattform-Regeln, Monetarisierung, Betrieb (geprüft, 02.10.2026)

**Schwellen für Einnahmen**
| Plattform | Bedingung |
|---|---|
| YouTube (Werbegeld) | 1.000 Abos **und** 4.000 Std. Wiedergabezeit (12 Monate) **oder** 10 Mio. Shorts-Aufrufe (90 Tage) |
| YouTube (Vorstufe, Fan-Funding) | 500 Abos, 3 Uploads in 90 Tagen, 3.000 Std. oder 3 Mio. Shorts-Aufrufe |
| YouTube **ab 01.02.2027**, neue Werbe-/Premium-Teilnehmer | **1.000 Abos und 8.000 qualifizierte Std. (365 Tage) oder 20 Mio. qualifizierte Shorts-Aufrufe (90 Tage)**; bestehender YPP-Status bleibt von dieser Eintrittsaenderung unberuehrt |
| TikTok Creator Rewards | 18+, 10.000 Follower, 100.000 Aufrufe in 30 Tagen; **nur Originalvideos über 1 Minute** werden bezahlt |
| Meta (Reels) | Schwellen je Programm, beim Einrichten prüfen |

**Folge für das Format:** Für TikTok-Einnahmen werden die Videos **länger als
60 Sekunden** gebaut (YouTube Shorts dürfen bis 3 Minuten).

**Betrieb (zusätzlich übernommen)**
- **Nicht 1:1 überall posten:** Titel, Beschreibung, Hashtags und Musik je
  Plattform anpassen.
- **Abwechslung erzwingen:** Stimme, Aufbau, Musik und Clips wechseln je Video
  (Teil der Wiederholungsprüfung).
- **Aufforderung (CTA)** am Ende: Abo, Kommentar, Link – kurz, nicht aufdringlich.
- **Fehlerbehandlung:** automatisch wiederholen, Protokoll, Push bei
  fehlgeschlagenem Upload.
- **Sicherung:** Skript, Rohdateien und Metadaten jedes Videos aufbewahren.
- **Steuern:** Einnahmen sind steuerpflichtig – ggf. Gewerbe anmelden, mit
  Steuerberater klären, bevor Geld fließt.

Quellen: [vidIQ – Partner Program 2026](https://vidiq.com/blog/post/youtube-partner-program-guide/), [subsub – Anforderungen 2027](https://www.subsub.io/blog/youtube-monetization-requirements), [postlinkapp – TikTok Creator Rewards](https://postlinkapp.com/blog/tiktok-creator-rewards-program), [toptal – Creator Rewards](https://www.toptal.com/creator/post/how-to-join-the-tiktok-creator-rewards-program)

Primaerquelle fuer YouTube 2027 (geprueft 05.10.2026):
[YouTube-Hilfe – Aenderungen am Partnerprogramm](https://support.google.com/youtube/answer/12843009).

---

## 2e. Weitere Open-Source-Pipelines geprüft (02.10.2026)

| Projekt | Lizenz | Was wir mitnehmen |
|---|---|---|
| youtube-agentic-ai-studio | MIT (laut Quelle; LICENSE-Datei vor Übernahme prüfen) | Animationen aus Standbildern (Zoom/Schwenk) als Ideengeber; Teile dürften mit Lizenzhinweis übernommen werden |
| AI-Reel-Factory | LICENSE vorhanden, Art noch zu prüfen | **Steuerung per Telegram** und **Google Chirp 3 HD** als Stimme |
| video-autopilot | keine sichtbar | nur Ideen (siehe 2a) |

**Übernommen:**
- **Freigabe auch per Telegram** (kostenlos): Das Video kommt mit Vorschau und
  Knöpfen **Freigeben / Ändern / Verwerfen** direkt in den Chat – ein Tipp,
  fertig. Ergänzt die Web-Push-Meldung des Dashboards.
- **Zweite Stimme zum Vergleich: Google Chirp 3 HD** – fast menschlich, **1 Mio.
  Zeichen/Monat kostenlos** (ca. 166.000 Wörter; ein Short hat ~120 Wörter →
  über 1.000 Shorts/Monat frei), danach 30 $ je 1 Mio. Zeichen. Wird im Pilot
  gegen Kokoro angehört; die bessere gewinnt. Hinweis: Google Cloud verlangt in
  der Regel ein Abrechnungskonto mit Karte, auch wenn im Freikontingent nichts
  anfällt – darum nur nach Rückfrage.

**Unser Vorteil gegenüber diesen Projekten:** Sie brauchen einen eigenen
Rechner, der läuft. Die Contentfabrik läuft in GitHub Actions + Cloudflare –
**kein PC nötig**, auch nachts und im Urlaub.

**Kostenstufen der anderen KI (zur Einordnung):** Wir bleiben bewusst im
0-€-Rahmen; bezahlte Stimmen (ElevenLabs), Schnitt-Apps oder fertige
Plattformen (Faceless.so, Fliki, HeyGen ab ca. 24–29 $/Monat) brauchen wir
nicht.

Quellen: [youtube-agentic-ai-studio](https://github.com/liolinv-sudo/youtube-agentic-ai-studio), [AI-Reel-Factory](https://github.com/ujala786hsp-wq/AI-Reel-Factory), [Google Cloud TTS – Preise/Freikontingent](https://texttolab.com/blog/google-cloud-tts-pricing), [diyai – Chirp 3 HD](https://diyai.io/ai-tools/audio-generation/google-cloud-text-to-speech-pricing/)

---

## 2f. Upload-Werkzeuge und Lizenzen für den Verkauf (geprüft, 02.10.2026)

**pendpost** (MIT, Open Source) – wird als Vorlage für unsere Upload-Stufe
genutzt (Code darf mit Lizenzhinweis übernommen werden):
- Freigabe ist **„fail-closed"**: ohne Freigabe-Status wird nie veröffentlicht.
- **Anti-Sperr-Sicherungen:** meldet Meta „Fehler 368" (Aktion blockiert),
  stoppt das Tool alle Meta-Uploads und startet **nicht** von selbst neu;
  Takt-Obergrenze verschiebt Uploads statt sie zu verwerfen; Not-Aus je
  Plattform.
- Unterstützt YouTube, Instagram, Facebook, LinkedIn (TikTok im Test).
→ Diese drei Sicherungen übernehmen wir in den Kontingent-Zähler (5a).

**Remotion** (Videos mit Code bauen): kostenlos nur für Einzelpersonen und
Firmen **bis 3 Mitarbeiter**; als SaaS-Automatisierung ab **100 $/Monat**.
→ **Nicht verwenden** – das kollidiert mit dem späteren Verkauf. Wir bleiben
bei ffmpeg (läuft als eigenes Programm auf dem Server; dabei entstehen keine
Lizenzpflichten für unseren Code).

**Bildquellen-Kontingente** (für den Zähler): Pexels 200 Anfragen/Stunde,
20.000/Monat; **Pixabay** als zweite Quelle (eigene Lizenz, gewerblich frei).

**Empfehlung der anderen KI, „ein fertiges Projekt klonen"** – nicht
übernommen: Die geprüften Projekte brauchen einen laufenden PC, nutzen teils
edge-tts (Grauzone) oder Bezahldienste zum Hochladen, und ihre Lizenzen sind
nicht alle für ein Verkaufsprodukt geeignet. Wir nehmen die **besten Teile mit
passender Lizenz** (pendpost-Sicherungen, Ideen aus youtube-agentic-ai-studio)
in die eigene Cloud-Pipeline, die schon läuft (Probelauf 1).

Quellen: [pendpost](https://github.com/pendpost/pendpost), [Remotion-Lizenz](https://www.remotion.pro/license), [Remotion – ist es kostenlos?](https://www.reactvideoeditor.com/blog/is-remotion-free)

---

## 3. Der Ablauf (für jeden Kanal gleich)

```
Thema ─► Skript + Faktencheck ─► Video bauen ─► Technik + KI-Pruefung
  ▲                                                   │
  │                                                   ▼
Auswertung ◄── Veroeffentlichen ◄── DEINE FREIGABE der fertigen Vorschau
```

1. **Thema finden** – aus Trends (YouTube-Suche, Google Trends, Reddit) und
   den eigenen Zahlen: was bei uns schon lief, bekommt Nachfolger.
2. **Skript** – KI schreibt nach Kanal-Vorlage (Ton, Länge, Aufbau, Haken in
   den ersten 3 Sekunden).
3. **Prüfung** – eine zweite KI-Lesung prüft Fakten, Wiederholung zu früheren
   Videos und Regel-Risiken.
4. **Bauen und fertiges Video pruefen** – Sprecherstimme, passende Clips/Bilder,
   Untertitel, Musik, Thumbnail; Technik messen und Video von der KI bewerten.
5. **Deine Freigabe** – fertige Vorschau aufs Handy. Heute pruefst und laedst
   du selbst hoch; geplant: **Freigeben / Aendern / Verwerfen** mit gespeichertem
   Status. Nichts geht ohne dich online.
6. **Hochladen** – zur geplanten Uhrzeit, je Plattform passend beschriftet,
   mit KI-Kennzeichnung („altered or synthetic content").
7. **Auswertung** – Aufrufe, Wiedergabezeit, Abos, Klicks, Leads – fließt in
   Schritt 1 zurück.

---

## 4. Regeln der Plattformen (geprüft) – und was daraus folgt

| Plattform | Regel | Folge für uns |
|---|---|---|
| **YouTube** | Uploads über die Schnittstelle aus **ungeprüften** Projekten sind **nur privat**, bis Google das Projekt prüft (kostenlos). 100 Uploads/Tag je Projekt. | Phase 0: Prüfung beantragen. Bis dahin: Tool lädt privat hoch, du schaltest in der YouTube-App öffentlich (1 Tipp). |
| **YouTube** | Regel „inauthentic content" (im Juli umbenannt aus „repetitious content"; die Quellen nennen 2025 bzw. 2026), seit 2026 verschärft durchgesetzt – gleichförmige Massenware wird nicht bezahlt, Kanäle werden gesperrt (Jan. 2026: Sperrwelle). KI erlaubt, wenn jedes Video eigenen Wert hat und gekennzeichnet ist. | Freigabe durch dich, Abwechslung erzwingen (Wiederholungsprüfung), max. 1 langes Video/Woche + 1 Short/Tag je Kanal, KI-Kennzeichnung immer an. |
| **TikTok** | Ohne geprüfte App: Posts nur **privat**, max. 5 Nutzer/Tag. Prüfung ca. 1–2 Wochen. | Prüfung in Phase 0 beantragen; bis dahin Entwurf + Push. |
| **Instagram** | Nur **Business-/Creator-Konten**; Video muss unter einer öffentlichen Adresse liegen. | Konten umstellen; Videos kurz auf Cloudflare R2 (kostenloser Speicher) ablegen. |
| **Facebook** | Seiten-Posts über Meta-App. | Mit Instagram zusammen einrichten. |
| **LinkedIn** | Posten im **eigenen Profil** freigeschaltet; **Firmenseite** braucht zusätzliche Freigabe. | Säule B startet über dein Profil. |

**Keine Klick-Roboter** (Skripte, die sich als Mensch ausgeben): Die
Plattformen erkennen das, und gesperrte Konten sind nicht zurückzuholen.

---

## 5. Technik – alles mit kostenlosen Bausteinen

| Teil | Womit | Kosten | Status |
|---|---|---|---|
| Dashboard, Login, Freigaben, Zeitplan | Cloudflare Worker + D1-Datenbank (wie Taktgeber) | 0 € | erprobt (Taktgeber) |
| Push aufs Handy | Web Push (wie Taktgeber) | 0 € | erprobt |
| Videos bauen | GitHub Actions (kostenlose Rechenminuten) + ffmpeg | 0 € | **ungeprüft: Minuten je Video messen** |
| Sprecherstimme | freie Sprachmodelle (Kandidaten: Kokoro, Piper) | 0 € | **ungeprüft: Qualität vergleichen** |
| Clips / Bilder | Pexels / Pixabay (freie Lizenzen, Schnittstelle) | 0 € | ungeprüft |
| Musik | lizenzfreie Bibliotheken (z. B. YouTube Audio Library) | 0 € | ungeprüft |
| Zwischenspeicher für Videos | Cloudflare R2 (10 GB frei) | 0 € | ungeprüft |
| Skripte, Themen, Prüfung | dein OpenAI-Schlüssel | Cent-Bereich, **wird gemessen** | erprobt (Sortidoc) |
| Hochladen | offizielle Schnittstellen | 0 € | Abschnitt 4 |

**Warum kein n8n:** braucht einen eigenen Server oder kostet als Cloud-Abo;
die Bausteine oben laufen ohne Server und ohne Abo.
**Warum kein Abacus.ai:** Abo; dein OpenAI-Schlüssel genügt.

---

## 4a. Qualität – höchste Qualität bei 0 € (Vorgabe des Nutzers)

**Grundsatz:** Kostenlos heißt nicht billig. Jedes Video muss gegen die
besten Faceless-Kanäle bestehen – sonst kein Wachstum und Sperr-Risiko
(YouTube bestraft gleichförmige Massenware, Abschnitt 4).

**Die besten kostenlosen Bausteine (geprüft, 2026)**

| Baustein | Wahl | Warum | Lizenz |
|---|---|---|---|
| Stimme | **Kokoro-82M** | beste Hörnote im Vergleich (MOS 4,2), 54 Stimmen, schneller als Echtzeit auf normalen Prozessoren, ohne Grafikkarte | Apache 2.0 – gewerblich frei |
| Stimme (Alternative) | Chatterbox | in Blindtests gegen ElevenLabs vorn, aber braucht Grafikkarte (4–8 GB) → erst mit eigenem Video-Server | MIT |
| Untertitel | **faster-whisper + ffmpeg** | wortgenaue Zeitmarken, animierte Wort-für-Wort-Untertitel (Stil der viralen Shorts) | MIT / LGPL |
| Clips & Bilder | Pexels / Pixabay | freie Lizenzen, über Schnittstelle | frei |

Nicht genommen: Piper (Qualität schwankt stark je Stimme, GPL-3.0),
XTTS v2 / F5-TTS (nur nicht-gewerblich).

**Qualitätskriterien – jedes Video wird dagegen geprüft, bevor es dir zur
Freigabe vorgelegt wird:**

1. **Haken in den ersten 2–3 Sekunden** (Frage, Zahl, Widerspruch).
2. **Tempo:** Bildwechsel alle 2–4 Sekunden, keine Standbilder über 5 s.
3. **Untertitel** Wort für Wort, groß, mittig, gut lesbar, synchron zur Stimme.
4. **Stimme** natürlich, Betonung geprüft, keine verschluckten Fachbegriffe.
5. **Bild passt zum Satz** (Clip-Suche je Satz, nicht je Video).
6. **Ton:** Lautheit nach Plattformnorm (YouTube ca. −14 LUFS), Musik leise
   unter der Stimme.
7. **Technik:** 1080×1920 (Shorts/Reels/TikTok) bzw. 1920×1080, 30 fps.
8. **Inhalt:** Fakten von der KI gegengeprüft, eigener Blickwinkel, keine
   Wiederholung früherer Videos (Ähnlichkeitsprüfung).
9. **Thumbnail/Titel** für lange Videos: klar, neugierig machend, nicht
   irreführend.
10. **Kennzeichnung** als KI-Inhalt, wo die Plattform es verlangt.

Punkte 2, 3, 6 und 7 prüft das Tool **automatisch** (messbar). Die übrigen
prüft die KI und zuletzt **du** bei der Freigabe. Was durchfällt, wird neu
gebaut, nicht vorgelegt.

**Im Pilot zu prüfen:** Klangqualität von Kokoro im direkten Vergleich, Zeit
pro Video auf GitHub Actions.

Quellen: [ocdevel – Open-Source TTS 2026](https://ocdevel.com/blog/20250720-tts), [localaimaster – 8 TTS getestet](https://localaimaster.com/blog/best-local-tts-models), [texttolab](https://texttolab.com/blog/open-source-text-to-speech), [ai-video-captions (Whisper + FFmpeg)](https://github.com/nicolaigaina/ai-video-captions), [ai-shorts-generator](https://github.com/AbdullahNaveed/ai-shorts-generator)

---

## 5a. Skalierung – von 2 Kanälen bis zum verkauften Produkt

Vom ersten Tag an so gebaut, dass **nichts neu geschrieben** werden muss,
wenn es wächst – nur Bausteine werden ausgetauscht.

**Fünf Bauprinzipien**

1. **Mandantenfähig ab Tag 1:** Arbeitsbereich → Marken → Kanäle →
   Plattform-Konten. Heute nur du; später jeder zahlende Kunde ein eigener
   Arbeitsbereich (Anmeldung, Abrechnung wie bei BusinessAssistant24).
2. **Kanäle sind Daten, kein Code:** Neue Nische, Sprache, Plattform = ein
   Formular im Dashboard, kein Programmieren.
3. **Alles läuft als Auftrag in einer Warteschlange** (Thema → Skript →
   Freigabe → Rendern → Upload). Fällt ein Schritt aus, wird er wiederholt;
   mehr Last = mehr Arbeiter, nicht anderer Code.
4. **Der Video-Bauer ist austauschbar:** derselbe Baukasten (ein Container)
   läuft heute kostenlos in GitHub Actions, später auf einem eigenen Rechner
   oder Server – ohne Änderung am Rest.
5. **Jede Plattform hat einen eigenen Kontingent-Zähler**, der die echten
   Grenzen kennt und Uploads verteilt statt sie scheitern zu lassen.

**Die geprüften Grenzen**

| Baustein | Grenze (kostenlos) | Quelle |
|---|---|---|
| YouTube-Upload | 100 Uploads/Tag **je Google-Cloud-Projekt** | Google, Juni 2026 |
| Instagram | 50–100 Posts je **Konto** in 24 h (Meta nennt beides) → wird je Konto live abgefragt | Meta |
| TikTok | nach Prüfung; vorher nur privat, max. 5 Nutzer/Tag | TikTok |
| GitHub Actions | **privates** Repo: 2.000 Min./Monat; danach 0,006 $/Min.; eigener Rechner als Arbeiter: unbegrenzt kostenlos | GitHub |

**Was das in Zahlen heißt** (Rechenminuten je Video = *m*, wird in Phase 1
gemessen):
- Kostenlose Videos pro Monat = 2.000 ÷ *m*. Beispiel: bei *m* = 3 sind es
  rund 660 Videos/Monat, also ca. 22 pro Tag.
- Darüber kostet ein Video *m* × 0,006 $ – bei *m* = 3 also knapp 2 Cent –
  oder 0 €, wenn ein eigener Rechner als Arbeiter mitläuft.

**Stufen**

| Stufe | Umfang | Was sich ändert | Fixkosten |
|---|---|---|---|
| **Start** | 2–3 Kanäle, ~5 Videos/Tag | nichts – alles im Gratis-Rahmen | 0 € |
| **Wachstum** | ~10 Kanäle, ~30 Videos/Tag | zusätzlicher Video-Arbeiter (eigener PC = 0 €, oder bezahlte Minuten); weitere Google-Projekte für YouTube | 0 € bis wenige € |
| **Produkt** | viele Kunden | Kunden-Anmeldung + Abrechnung, eigener Video-Server, ggf. bezahlter Cloudflare-Tarif; jeder Kunde verbindet **seine** Konten (dann zählen die Grenzen je Kunde) | wird aus Kundeneinnahmen bezahlt |

**Ziel Verkauf (Abo, monatlich) – vom Nutzer bestätigt:** Für die Stufe
„Produkt" wird jede Plattform-App strenger geprüft, sobald **fremde Kunden**
ihre Konten verbinden (Google-OAuth-Verifizierung für den Upload-Zugriff,
Meta App Review, TikTok-Prüfung für mehrere Nutzer). **Vor dieser Stufe
prüfen:** genaue Anforderungen und ob dabei Kosten entstehen (z. B.
Sicherheitsprüfungen). Bis dahin nutzt nur der Betreiber das Tool.

**Ungeprüft und deshalb im Pilot zu messen:** Rechenminuten je Video,
Grenzen des kostenlosen Cloudflare-Tarifs bei vielen Kanälen, Qualität der
freien Stimmen.

Quellen: [GitHub Actions billing](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions), [cicdcalculator](https://cicdcalculator.com/github-actions-free-tier), [Instagram-Limits](https://postproxy.dev/blog/instagram-reels-api-publishing-guide/), [keyapi](https://www.keyapi.ai/blog/instagram-api-rate-limits-2026-what-changed-and-how-to-adapt/), [YouTube-Quota](https://outlierkit.com/resources/youtube-api-quota/)

---

## 6a. Kanal-Dashboard – alle Zahlen je Kanal (Vorgabe des Nutzers)

Jeder Kanal hat eine eigene Seite. Oben die **Ampel** (läuft / Achtung /
Problem), darunter:

**Wachstum und Geld**
| Kennzahl | YouTube | Instagram | TikTok | Facebook |
|---|---|---|---|---|
| Aufrufe | ✓ | ✓ („Views") | ✓ | ✓ |
| Wiedergabezeit, Ø Wiedergabedauer | ✓ | Ø Wiedergabe, Abschlussrate | – | ✓ |
| Abos / Follower gewonnen | ✓ | ✓ | ✓ | ✓ |
| Likes, Kommentare, Teilen, Speichern | ✓ | ✓ | ✓ (ohne Speichern) | ✓ |
| Thumbnail-Impressionen + Klickrate | ✓ (seit 15.01.2026 in der Schnittstelle) | – | – | – |
| **Einnahmen** (geschätzt) | ✓ sobald monetarisiert | – | – | – |

Einschränkung laut Quellen: Instagram liefert Reel-Auswertungen erst ab
**1.000 Followern**; davor zeigt das Dashboard nur die öffentlichen Zahlen.

**Selbst berechnet (unabhängig von den Plattformen)**
- **Fortschritt zur Monetarisierung** (Balken bis zur YouTube-Schwelle)
- **RPM** = Einnahmen ÷ Aufrufe × 1.000, je Video und Kanal
- **Kosten je Video** (KI-Abrechnung, Rechenminuten) und **Gewinn je Kanal**
- **Bestes / schlechtestes Video** der Woche, mit Thema und Haken
- **Themen, die funktionieren** (fließt in die Themenwahl zurück)
- **Takt**: geplant / freigegeben / veröffentlicht / fehlgeschlagen
- **Regel-Risiko**: Ähnlichkeit zu früheren Videos, KI-Kennzeichnung gesetzt,
  Warnungen der Plattformen
- **Kontingente**: verbrauchte Uploads/Tag je Plattform, Rechenminuten im Monat

**Gesamtübersicht** über alle Kanäle: Summen, Vergleich der Kanäle
nebeneinander, Trend der letzten 7/28/90 Tage, Monatsbericht aufs Handy.

Quellen: [YouTube Analytics – Metriken](https://developers.google.com/youtube/analytics/metrics), [Instagram Insights (Meta)](https://developers.facebook.com/docs/instagram-platform/insights/), [Reels-API-Leitfaden](https://www.getphyllo.com/post/a-complete-guide-to-the-instagram-reels-api), [TikTok Video-Objekt](https://developers.tiktok.com/doc/tiktok-api-v2-video-object?enter_method=left_navigation)

---

## 6. Das Dashboard (für dich, vom Handy aus)

1. **Freigaben** (Startseite): Karten mit Video-Vorschau, Skript, Plattformen,
   geplanter Zeit – **Freigeben · Ändern (Wunsch eintippen) · Verwerfen**.
2. **Kalender**: was wann wo erscheint, je Kanal farbig.
3. **Kanäle**: je Kanal Nische, Ton, Sprache, Plattformen, Takt – anlegen ohne
   Programmieren.
4. **Zahlen**: Aufrufe, Wiedergabezeit, Abos, Einnahmen (sobald freigeschaltet),
   **Leads** (Säule B), Kosten je Video.
5. **Ideen**: Themenvorschläge, die du nach oben/unten schieben kannst.
6. **Status**: läuft alles? (letzter Lauf, Fehler, Prüfstatus der Plattformen)

---

## 7. Was du einmalig tun musst (kein Programmieren)

1. **Konten**: Je Kanal ein YouTube-Kanal (mehrere Kanäle unter einer
   Gmail-Adresse möglich); Instagram auf **Business** stellen und mit einer
   Facebook-Seite verbinden; TikTok-Konten; LinkedIn-Profil.
   Deine alten Gmail-Konten sind dafür gut geeignet.
2. **Entwickler-Zugänge** (ich führe Schritt für Schritt): Google Cloud
   (YouTube), Meta (Instagram/Facebook), TikTok, LinkedIn – alle kostenlos.
3. **Prüfungen beantragen** (YouTube, TikTok) – dafür baue ich eine kleine
   Website mit Datenschutzerklärung und Nutzungsbedingungen (kostenlos auf
   Cloudflare).

---

## 8. Phasen – mit Erfolgskriterien

| Phase | Inhalt | fertig, wenn … |
|---|---|---|
| **0 – Vorbereitung** | Konten, Entwickler-Zugänge, Website, Prüfungen beantragen | alle Anträge gestellt |
| **1 – Erster Kanal** | Dashboard + Freigabe + „AI Tools Explained": täglich 1 Short auf YouTube | 14 Tage täglich ohne Eingriff außer Freigabe |
| **2 – Säule B** | „BusinessAssistant24"-Kanal (DE) auf LinkedIn + YouTube | erster Lead aus einem Beitrag |
| **3 – Breite** | Instagram, Facebook, TikTok (nach Prüfung); 2. Säule-A-Kanal; lange Videos | 4 Plattformen laufen automatisch |
| **4 – Lernen** | Auswertung steuert Themenwahl | Themen mit Daten statt Zufall |

Nach **60 Tagen** je Kanal entscheiden: weiter, ändern oder einstellen – nach
Zahlen.

---

## 9. Risiken – ehrlich

- **Schnelles Geld ist nicht garantiert.** YouTube bezahlt erst ab einer
  Mindestzahl an Abos und Wiedergabezeit (Partnerprogramm; die genauen
  Schwellen prüfe ich vor dem Start in der YouTube-Hilfe) – realistisch Monate. Säule B kann früher wirken (Leads).
- **Sperr-Risiko** bei Massenware → Freigabe, Abwechslung, Kennzeichnung,
  maßvoller Takt.
- **Plattform-Prüfungen** können abgelehnt werden → dann Entwurf + Push, du
  veröffentlichst mit einem Tipp.
- **Kostenlose Kontingente** (GitHub-Minuten, R2) können knapp werden → wird
  in Phase 1 gemessen.

---

## 10. Entscheidungen

**Getroffen (02.10.2026):**
- **Säule A zuerst.** Säule B (BusinessAssistant24, Sortidoc) kommt erst, wenn
  beide Tools von echten Kunden getestet sind.
- Start-Nischen: **„AI Tools Explained"** und **„Business Origin Stories"**
  (Englisch) – nach 60 Tagen anhand der Zahlen prüfen.
- Freigabe am Anfang: **jedes Video einzeln**.

**Noch offen:**

1. Säule-A-Start mit **„AI Tools Explained" + „Business Origin Stories"** (EN)?
2. Säule B zuerst für **BusinessAssistant24** oder **Sortidoc**?
3. Name des Tools („Contentfabrik" ist nur ein Arbeitstitel)?
4. Freigabe: jedes Video einzeln (empfohlen am Anfang) oder später
   „automatisch, wenn die Prüfung grün ist"?

---

## Quellen

- RPM-Daten: [fliki](https://fliki.ai/blog/best-faceless-youtube-niches), [youtubeniches.com](https://youtubeniches.com/blog/best-faceless-youtube-niches-2026), [depthhq](https://depthhq.com/blog/best-faceless-youtube-niches-2026), [fluxnote](https://fluxnote.io/guides/profitable-faceless-youtube-channel-niches), [outlierkit (Schlaf)](https://outlierkit.com/resources/use-cases/ai-sleep-relaxation-youtube/)
- YouTube „inauthentic content": [invideo](https://invideo.io/blog/youtube-kills-ai-faceless-channels/), [lenspov](https://lenspov.com/articles/youtube-ai-content-demonetization-2026), [TubeBuddy](https://www.tubebuddy.com/blog/youtube-ai-demonetization-policy-meaning/)
- YouTube-Schnittstelle (privat bis Prüfung, Kontingent): [Google Developers – Videos](https://developers.google.com/youtube/v3/docs/videos), [outlierkit – Quota](https://outlierkit.com/resources/youtube-api-quota/)
- TikTok (privat bis Prüfung): [postpeer](https://www.postpeer.dev/blog/best-tiktok-posting-api), [vorplabs](https://vorplabs.com/agent-tools/tiktok-content-posting-api)
- Instagram/Meta: [postproxy](https://postproxy.dev/blog/social-media-platform-api-rules-rate-limits-media-specs/)

---

## Messung Probelauf 1 (02.10.2026, GitHub Actions, Lauf 37013126621)

Test-Short im Ranking-Format, 45,2 s, 1080×1920, 30 fps, 122 Wörter.

| Stufe | Sekunden |
|---|---|
| Stimme laden (Kokoro) | 3,6 |
| Stimme erzeugen | 27,6 |
| Wort-Zeitmarken (faster-whisper) | 10,3 |
| Bilder | 0,4 |
| Rendern (ffmpeg, Lautheit −14 LUFS) | 27,9 |
| **Video gesamt** | **69,7** |
| **Lauf gesamt inkl. Einrichtung** | **ca. 132 (2,2 Min.)** |

**Ergebnis:** *m* ≈ 2,2 Rechenminuten je Video → rund **900 Videos/Monat
kostenlos** (2.000 Min. ÷ 2,2). Mehrere Videos je Lauf senken *m* weiter
(Einrichtung nur einmal).

**Gefunden – noch zu verbessern:**
1. Zweite Titelzeile zu breit, an den Rändern abgeschnitten → Schriftgröße
   automatisch anpassen.
2. Standbilder statt Clips → verletzt Kriterium „Bildwechsel alle 2–4 s"
   (Abschnitt 4a). Nächster Schritt: Videoclips (Pexels) bzw. Bewegung.
3. Stimme: Bewertung durch den Betreiber steht aus.

## Messung Probelauf 3 (02.10.2026) – mit Pixabay-Clips

Test-Short 45,2 s, 7 Abschnitte, je ein passender Pixabay-Clip (Quellen in
`quellen.json`). Titel passt jetzt in die Breite; Ton 48 kHz Stereo.

| Stufe | Sekunden |
|---|---|
| Stimme (Kokoro) | 23,2 |
| Zeitmarken | 7,4 |
| Clips suchen, laden, zuschneiden | 45,2 |
| Rendern | 74,0 |
| **Video gesamt** | **149,8** |

*m* steigt damit auf ca. 3,5 Rechenminuten je Video (inkl. Einrichtung) →
rund **570 Videos/Monat kostenlos**. Beschleunigung möglich: Rendern mit
schnellerer Voreinstellung, mehrere Videos je Lauf, Clips aus dem
Zwischenspeicher. Gefunden: Pixabays Schutzdienst blockt die
Standard-Kennung von Python (403/1010) → eigene Kennung.

## Entscheidung Stimmen (02.10.2026, Hörprobe des Betreibers)

Natürlichste Kokoro-Stimmen laut Betreiber: **bf_emma (Frau, UK),
am_michael (Mann, US), bm_george (Mann, UK)**. → Google Chirp wird **nicht**
gebraucht (keine Google-Cloud-Karte nötig).

| Kanal | Stimmen (abwechselnd) |
|---|---|
| AI Tools Explained | am_michael, bf_emma |
| Business Origin Stories | bm_george |

## Messung Skript-Baustein (02.10.2026)

- **Gemini kostenlos:** schreibt Skripte (gemini-flash-latest, 3-flash-preview);
  gemini-2.5-flash ist für neue Konten gesperrt, 3.8-flash zeitweise
  überlastet (503) → Modell-Kette mit Wechsel.
- **Internetsuche (Grounding) im Gratis-Rahmen: nicht verfügbar** (429
  „quota exceeded"), geprüft mit zwei Modellen.
- **Faktenprüfung wirkt:** bei „Top 5 AI Video Tools" veraltete Aussagen
  (Runway, Sora) gefunden → kein Video.
- **Folge:** „Business Origin Stories" (stabile Fakten) läuft mit Gemini
  kostenlos. „AI Tools Explained" braucht aktuelle Suche → Entscheidung des
  Betreibers offen (siehe Chat): bezahlte Suche (Cent-Bereich) oder Start
  nur mit Geschichten-Kanal.

## Ideen-Speicher (Stand 03.10.2026)

Gesammelt aus Hinweisen anderer KIs, YouTube-Videos und eigenen Messungen.
Nur was Qualitaet oder Automatik hebt und kostenlos/gewerblich nutzbar ist.

**Umgesetzt**
- Countdown-Ranking, Nutzen zuerst, Blickwinkel je Tag, Loop-Ende, Floskel-Sperre
- Quellen-Methode fuer beide Kanaele (KI: GitHub/Hugging Face/Hacker News; Business: Wikipedia)
- Bewegter Hintergrund, Karten-Einflug, Zoom auf jedem Clip, keine leeren Flaechen
- Montserrat, ruhige Wort-Untertitel aus dem Skripttext, Knopf-Zone frei
- Automatische Qualitaetspruefung (Gemini sieht das Video + Technik-Messung)
- Planungszeit je Kanal in Telegram (Publikum USA)

**Als Naechstes (kostenlos)**
1. Echte Fotos fuer Firmengeschichten: Wikimedia Commons / Openverse (freie Lizenzen,
   Namensnennung automatisch in die Beschreibung)
2. Stimme lebendiger: andere Kokoro-Stimmen/Tempo testen, Pruefung entscheidet
3. Product Hunt (offizielle API, kostenloses Konto) als Quelle fuer Verbraucher-Apps
4. Formate fuer den KI-Kanal: „A vs. B", „kostenlose Alternative zu ...", „gerade erschienen"
5. Musik nur mit sicherer Lizenz (Content-ID-Risiko vorher pruefen)
6. Pruefung mit Selbstkorrektur: Probleme mit Zeitstempel -> betroffene Clips neu waehlen
7. Dashboard mit YouTube Analytics: welche Themen/Hooks laufen -> mehr davon

**Bewusst nicht** (Gruende in den Commit-Nachrichten und im Chat)
- KI-Videogeneratoren (Veo, Pika, Kling, Hailuo, Runway, LTX, Seedance): kleines
  Kontingent, Wasserzeichen oder keine gewerblichen Rechte, keine Gratis-Schnittstelle
- Mehrere Gratiskonten zum Kontingent-Zuruecksetzen: Verstoss gegen Nutzungsbedingungen
- edge-tts (inoffizieller Zugang), Remotion (fuer Firmen kostenpflichtig), Ayrshare/
  Buffer (Upload kostenpflichtig/begrenzt), n8n (eigener Server), Video Autopilot (keine Lizenz)
- Facecam/Selbstversuch-Formate (nicht faceless, nicht automatisierbar)
