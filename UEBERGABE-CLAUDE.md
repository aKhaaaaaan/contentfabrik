# Uebergabe an Claude – Contentfabrik

Stand: 05.10.2026, nach Uebernahme der Vorarbeit und der neuen Qualitaets-
und Formatverbesserungen. Dieses Dokument wird mit den Pilot-Ergebnissen
aktualisiert. Es enthaelt keine Zugangsschluessel.

## Nutzerauftrag und zugesagtes Ergebnis

### Auftrag vom 06.10.2026: Qualitaetsserie im normalen Tageslauf

Der Nutzer hat den vorgeschlagenen Test mit drei automatisch entstandenen
Videos je Kanal und anschliessender Konsistenzpruefung beauftragt. Die
vollstaendige Beschreibung steht in [QUALITAET-AUTOMATIK.md](QUALITAET-AUTOMATIK.md).
`video.yml` erfasst jetzt jeden Produktionslauf, auch Fehlschlaege, ueber
`fabrik/qualitaetsserie.py`. Dauerhafter Verlauf: `verlauf/qualitaetsserie.json`.
Keine manuelle Skript-/Bildregie, keine Budgetumgehung, keine Pilot-Erfolge
hineinrechnen. Ein Video je Kanal und Produktionstag anstreben; Kontingente
koennen die drei Videos je Kanal verzoegern.

KI-Pruefung ist keine menschliche Sichtpruefung. Erst nach vollstaendigem
Ansehen und Hoeren das konkrete Video mit Hash bewerten. Zehn bestandene,
unterschiedliche Shorts je Kanal ohne menschliche Nachbearbeitung sind der
spaetere Kontrollpunkt; das schaltet keinen Plattform-Upload frei und beweist
keine Langvideo-Qualitaet. Fehlversuche bleiben sichtbar, neue Produktions-
versionen beginnen die bestaetigte Folge neu. Ziel 10/10, Versandfilter ab 7/10
unveraendert. Es wurden damit noch keine sechs neuen Videos fertiggestellt.
Erster echter Start: `video.yml` mit `kanal=alle`, leerem Thema, am 06.10.
um 10:14:44 Berlin, Run `37434817863`, Code `9dd5d63`. Anfangsstatus auf
GitHub `in_progress`; Ergebnisse nicht vorwegnehmen. Die Tageszeitplaene
setzen die Serie innerhalb der bisherigen Budgets fort.

### Automatisierung und manuelle Plattform-Uploads, 05.10.2026

Der Nutzer meldet: "Läuft das jetzt voll automatisiert? weil ich die beide
videos manuell hochgeladen habe, sowhol auf youtube als auch auf tiktok".
Damit sind fuer beide zuletzt gelieferten Videos manuelle YouTube- und
TikTok-Uploads als Nutzerangabe erfasst. Video-IDs, URLs und Sichtbarkeit
sind unbekannt; keine Plattform-Verifikation behaupten und nichts doppelt
hochladen. Die Zuordnung zu den gelieferten Dateien steht in
`verlauf/telegram-sendungen.json`.

Pruefung am 05.10.2026: `video.yml` und `themen.yml` sind auf GitHub aktiv.
Die taegliche Pipeline kann Themen, Skripte, Bilder, Ton, Video,
Qualitaetspruefung und Telegram-Zustellung automatisch abarbeiten, sofern
Quellen, Kontingente und Qualitaetsfilter den Lauf zulassen. Plattform-Uploads
sind nicht an `fabrik/lauf.py` angeschlossen; Veroeffentlichung bleibt manuell.
`gesendet` bedeutet ausschliesslich Telegram-Zustellung.

Der letzte gepruefte zeitgesteuerte Tageslauf
[37362911521](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37362911521),
gestartet um 19:22:14 UTC, hat die Vorpruefung bestanden und die Produktion
uebersprungen. Die Vorpruefung nimmt Kanaele mit bereits heute gesendetem
Video aus; ein erfolgreicher GitHub-Lauf bedeutet hier kein neues Video.
Die beiden verbesserten Piloten wurden manuell gestartet, visuell kontrolliert
und separat auf Telegram geschickt. Sie belegen noch keine gleichbleibende
Qualitaet der automatischen Tagesproduktion. Die neuen Motivziele sind
gespeichert, aber noch nicht als neue Videos umgesetzt.

Der Cloudflare-Zeitplan-Worker liegt als Code vor; eine aktive Deployment-
und Cron-Konfiguration wurde nicht verifiziert. YouTube-Auswertung ist
implementiert, aber erfolgreiche Datenerfassung fuer die jetzt manuell
hochgeladenen Videos wurde nicht bestaetigt.

### Neueste Nutzerrueckmeldung am 05.10.2026: deutliche Verbesserung bestaetigt

Der Nutzer bestaetigt ausdruecklich, dass **beide neuen Videos angekommen sind
und ihm viel besser gefallen als vorher**. Es bleibt Luft nach oben und das
gemeinsame Qualitaetsziel ist weiterhin **10/10**. Das ist ein Ziel, keine
vergebene Nutzernote: die tatsaechlichen KI-Noten bleiben 8/10, eine numerische
Nutzerbewertung wurde nicht genannt. Der bestehende Versandfilter ab 7/10 mit
Fakten-/Technikpruefung bleibt unveraendert; 10/10 nicht zum neuen Versandhindernis machen.

| Kanal | Bestaetigter aktueller Stand | Vorgabe fuer kuenftige vergleichbare Shorts |
|---|---|---|
| AI Tools Explained | 23 Einstellungen, 12 unterschiedliche Motive; deutlich besser | Etwas mehr Bildvielfalt: etwa **14-18 wirklich unterschiedliche, passende Motive** |
| Business Origin Stories | 24 Einstellungen, 14 unterschiedliche Motive; positiv bewertet | **Neuere Vorgabe: etwa 24 Einstellungen mit 18 unterschiedlichen Motiven** anstreben |

Fuer AI also 2-6 weitere sinnvolle Motive in kuenftigen vergleichbaren Videos
einplanen, statt dieselben Bilder erneut einzusetzen. Originale Handlungsszenen,
Objekt-/Prozessdetails oder echte quellenbelegte Tool-Beispiele nutzen; keine
erfundenen Outputs. Zoom, Zuschnitt und neue Beschriftung sind kein neues Motiv.
Die Zahlen beziehen sich auf die bisherigen Shorts um 82 bzw. 90 Sekunden;
andere Laengen nach Erzaehlung planen. Der Nutzer hat Business anschliessend
ausdruecklich auf etwa **24 Einstellungen mit 18 Motiven** weiterentwickelt:
vier zusaetzliche passende Motive statt Bildwiederholungen. Die fruehere Aussage
"24 Einstellungen mit 14 Motiven passt perfekt" bleibt historische positive
Rueckmeldung; sie ist nicht mehr das aktuelle Planungsziel. Motive sinnvoll
in die Sprechphasen integrieren, ohne fuer eine Zahl unpassende Bilder einzufuegen.
GTA-artige eigene Figuren/Spielwelt, Figuren am Einstieg und im Verlauf,
passende Musik/Soundeffekte und gesprochene like/share/save-Aufrufe erhalten.
Weiter an Skript, Bild-Sprechtext-Zuordnung, Spannungsbogen und Feinschliff arbeiten.

Wortgetreue Rueckmeldung ist fuer beide konkreten Video-SHA256 in
`lernen/redaktion.json` gespeichert, getrennt vom frueher abgelehnten 17:35-Video.
Die neuen Regeln werden bereits durch `lernen.redaktionsregeln()` an Autor,
Bildplaner und Kritiker weitergegeben. Strukturierte Kanalvorgaben dokumentieren
14-18 als AI-Planungsziel, 24/14 als gelieferte Business-Referenz und jetzt
24/18 als neueres Business-Planungsziel.
`verlauf/telegram-sendungen.json` haelt zusaetzlich die Empfangsbestaetigung und
qualitative Bewertung des Nutzers fest. Originale Ist-Zahlen und KI-Noten
bleiben erhalten. Die bestehende Qwen-Pilotvorlage hat weiter 12 Motive:
14-18 ist das naechste AI-Planungsziel, noch kein bereits erzeugtes neues Video.
Auch die Nintendo-Pilotvorlage und die gelieferte Business-MP4 bleiben beim
tatsaechlichen Stand 24/14; ein neues Video mit 18 Motiven wurde noch nicht gebaut.

### Technische Umsetzung und Tests fuer Claude

Die gebauten Module, ihre Aufgaben, Datenfluss, Bilder/Prompts, Lernregeln,
Qualitaetskontrollen, Telegram-Zustellung sowie Testbefehle und Ergebnisse
sind zusammenhaengend in [UMSETZUNG-UND-TESTS.md](UMSETZUNG-UND-TESTS.md)
dokumentiert. Dort stehen auch die naechsten konkreten Arbeiten fuer
AI 14-18 Motive und Business 24/18. Bei Uebernahme zuerst den neuesten
Nutzerauftrag hier, danach diese technische Referenz lesen.

### Abgeschlossener Stand am 05.10.2026, 20:34 Berlin

Code und 16 Bilder sind auf GitHub (`5e3940a`, dann `01d31e7`), 154 lokale
Regressionstests und beide GitHub-Pruefläufe erfolgreich. **Beide neuen
Shorts sind fertig, visuell kontrolliert und tatsaechlich auf Telegram zugestellt.**

| Kanal | Produktion | KI Story / Video | Echte Bildfolge | Telegram-Bestaetigung |
|---|---|---|---|---|
| AI Tools Explained, Qwen-Bildworkflow | 37353822179 | 8 / 8 | 23 Einstellungen, 12 Motive, 82,2 s | Versand 37355648862, message_id 123, 20:24:57 Berlin |
| Business Origin Stories, Nintendo-Karten | 37354061119 | 8 / 8 | 24 Einstellungen, 14 Motive, 89,7 s | Versand 37356701658, message_id 130, 20:33:15 Berlin |

Fakten- und Technikpruefung ohne offene Befunde. Beide: 1080x1920, H.264,
30 fps, AAC Stereo 48 kHz; AI -14,9 LUFS, Business -14,1 LUFS. Alle
Video-Einzelkategorien >=8; keine offenen Videoprobleme laut KI-Pruefung.
Business-Story hat Spannung/Teilbarkeit jeweils 7, alle weiteren Storywerte
mindestens 8. Der Story-Kritiker schlaegt vor, die spaetere Disney-Partnerschaft
kausal als erzwungene Wiederkaeufe zu beschreiben. Diese Absicht ist NICHT
belegt und darf nicht ungeprueft in ein Skript/Lernregel uebernommen werden.
Der gelieferte Text behauptet diese Kausalitaet nicht.
Diese Noten sind KI-Urteile, KEINE Nutzerbewertung und KEINE Retentionsdaten.
Keine Zusicherung, dass Videos immer ueber 8 liegen. Zum Versandzeitpunkt war
das Nutzerurteil noch offen; die anschliessende positive Rueckmeldung steht oben
und hat weiterhin Vorrang vor KI-Urteilen. Das alte 17:35-Video wurde NICHT erneut gesendet.

Codex hat echte Frames beider fertigen MP4s im 4-Sekunden-Abstand kontrolliert:
passende Hauptbilder ueber die ganze Laenge, mehrere Motive innerhalb der
Sprechphasen, keine Kerzenstrecken, eigene Figuren am Einstieg und im Verlauf.
Feste Herkunftslabels unterscheiden illustrative Szenen von vier echten
Qwen-Modellkartenbeispielen. Kamera-/Schnittbewegung, keine volle Koerperanimation.
Beide enthalten eigene passende Instrumentalmusik, Ducking, Soundeffekte und
den gesprochenen like/share/save-Aufruf. Telegram-Versand bestaetigt
API-Erfolg und hat anschliessend die kompletten Skripte/Uploadtexte versendet.

Lokal: `ausgabe/github/11363059750/ausgabe/short.mp4` (AI) und
`ausgabe/github/11364637569/ausgabe/short.mp4` (Business). Die jeweiligen
Ordner enthalten echte Kritik, Messung, Skript und Bildablauf.
Kontaktboegen: `ausgabe/videoanalyse/ai-neu-kontaktbogen.jpg` und
`ausgabe/videoanalyse/business-neu-kontaktbogen.jpg`.
Zustellbelege mit unveraenderten Video-SHA256/Ist-Zahlen in `verlauf/telegram-sendungen.json`;
beide bestaetigten Zustellungen auch im jeweiligen Kanalverlauf eingetragen,
ohne alte Videos oder abweichende Nutzerurteile zu ueberschreiben.

Die globale GitHub-Concurrency laesst einen aktiven UND einen wartenden Pilot
zu. Ein dritter Start ersetzt den bisherigen wartenden Run, auch bei
cancel-in-progress=false. Daher nicht mehrere wartende Starts aneinanderreihen:
erst aktiven Status abwarten und dann hoechstens einen weiteren einreihen.
37353584318 wurde wegen eines wiederholten echten Demo-Bildes abgebrochen;
37353589075 wurde als wartender Run durch den korrigierten AI-Start ersetzt.
Die Qwen-Regie verwendet jetzt alle vier echten Demo-Bilder jeweils genau
einmal; ein Test verhindert diese doppelte Demo-Auswahl.

Vor dem Bibliothekswechsel war kein verbesserter Pilot zugestellt. Der fruehere AI-Lauf
37348937412 stoppte vor der MP4: Cloudflare meldete das erschoepfte freie
Tageskontingent. Wiederholte Starts mit demselben Generator helfen heute nicht.
Keine kostenpflichtige Hochstufung oder Billing-Aenderung vorgenommen.

Stattdessen 16 Originalillustrationen mit built-in image_gen erzeugt, gesichtet
und im Projekt gespeichert (`assets/illustrationen/`). Exakte Prompts in
`PROMPTS.json`, `ERWEITERUNG-PROMPTS.json`, `BUSINESS-FIGUR-PROMPTS.json`.
Der Katalog enthaelt SHA256, Kanal, Dateiname und Motiv; die Freigabe bezeichnet
eine Sichtkontrolle, KEINE KI-Note oder garantierte Zuschauerqualitaet.
Fremde IDs, andere Kanaele, Pfadausbruch und spaeter veraenderte Bilder werden
von `bibliothek.bild` abgewiesen. Neues Bildmodus `asset`, im Endvideo als
ILLUSTRATION markiert. Die source-echten Qwen-Beispiele tragen weiter
MODEL CARD EXAMPLE. Keine eigene Illustration als echter Qwen-Test ausgeben.

`pilot_bildregie.py` ordnet beide Vorlagen konkret pro Sprechphase zu: mehrere
Motive, eigene Figuren am Einstieg und wiederkehrend im Verlauf. Vollstaendige
Regievorgaben brauchen keinen zweiten Gemini-Auftrag; automatische Skripte
erhalten weiter einen Gemini-Bildplan und den passenden Bibliothekskatalog.
Eine zu kurze konkrete Bildfolge stoppt statt beliebiger Bilder/Nachgenerierung.
Neue historische Vergleichsgrafiken zeigen qualitative Unterschiede bei Karten
und Preis, keine erfundenen Preise. Auch hier Bildvielfalt/volle Abdeckung pruefen.

Der Nutzer hat beide bisherigen Referenzfiguren mit Screenshots bestaetigt:
Business: Hut/Anzug/Taschenuhr; AI: Lederjacke/leuchtende Brille. Originaldateien
in `figuren/` stimmen damit ueberein. Eigene Handlungsszenen behalten die Identitaet.
Die gemalte Open-World-Spielwelt ist bevorzugt; Fakten und echte Tool-Demos bleiben
quellengetreu. Nur Kamera-/Schnittbewegung, keine behauptete volle Figurenanimation.
Diese Vorgaben stehen persistent auch in `lernen/redaktion.json` und erreichen
Skriptautor, Bildplaner und Kritiker. Bei neuen Presenter-Illustrationen kann
der Planer jetzt `figur=true` waehrend des Verlaufs setzen: die vorhandene
Referenzdatei wird dann tatsaechlich uebergeben, nicht nur am Anfang/Ende.

**Wichtiges frueheres Nutzerfeedback: Das um 17:35 versandte Nintendo-Video wurde als
deutlich schlechter als 5/10 abgelehnt. Seine Rueckmeldung hat Vorrang vor
der historischen KI-Note 9.** Kontaktbogen der echten MP4 bestaetigt rund
27 Sekunden ohne passendes Hauptbild, Kerzenhintergrund und mehrere
12-15-Sekunden-Einstellungen. Dieses Video nicht als professionell oder
Qualitaetserfolg darstellen und nicht erneut verschicken. SHA256-Sperre
und wortgetreues Feedback in `lernen/redaktion.json`.

Zusatzauftrag: mehrere Bilder INNERHALB einer Sprechphase; Gemini Flash
soll den Bildplan erstellen. Dazu ein guter Short fuer AI Tools Explained.

Weitere Korrektur nach gescheiterten Piloten: AI-Lauf 37341670490 wurde mit
Story 4/10 vor dem Render gestoppt. Nur Likes/Downloads/Tasknamen belegen
keinen praktischen Nutzen. `trends.beschreibung` liest jetzt die primaere
README/Modellbeschreibung, entfernt Code/Benchmarktabellen und markiert nur
ausreichend beschriebene Quellen als belegt. Rankings waehlen genau eine
Quelle/Kennzahl, niemals GitHub-Sterne mit HF-Likes mischen; Shorts behandeln
drei ausreichend belegte Tools. LTX-README aktuell nicht frei abrufbar:
kein Umgehen einer Zugangsbeschraenkung, kein erfundener Nutzen.
Business-Lauf 37341676776 ebenfalls vor Render gestoppt: Story insgesamt 7,
nur Teilbarkeit 6. Gesamt- und Videogrenze bleiben 7, Story-Teilbarkeit darf
als unsichere Prognose 6 sein; alle anderen Kategorien weiterhin 7.
Demo-Auswahl schliesst bereits benutzte Beispielbilder aus. Erklaerende
AI-Illustrationen sind als ILLUSTRATION markiert und duerfen keine erfundenen
Tool-Interfaces oder Outputs zeigen. Bei nicht erreichbarer Openverse-Musik
erzeugt `ton.musikbett` eigene instrumentale Hintergrundmusik ohne fremde
Samples; bestehendes Ducking/Fades und Lautheitsmessung bleiben aktiv.
Promptversion jetzt `2026-10-05.8`; 142 Regressionstests bestanden.
Neue Piloten auf `d5437c3`: AI Tools Explained
[37344285206](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37344285206),
danach Business/Nintendo
[37344290208](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37344290208).
Beide ohne automatischen Telegram-Versand. CI 37344257003 bestanden.
Diese Starts belegen noch kein fertiges Video und keine Zustellung.
AI-Lauf 37344285206 ist ebenfalls vor Render gescheitert (Story 5/10): der
Autor blieb trotz besserer Quellen bei technischen Kategorien statt Nutzen.
Neue gezielte Vorlage `piloten/qwen-bildworkflow.json`: einzelne Bild-KI,
Cutouts/gezielte Bearbeitung/Referenzen, konkrete dokumentierte Beispiele,
ehrlicher Hinweis auf Herstellerbeispiele und Research License. 201 Woerter.
`pruefungen/qwen_vorlage.py` erstellt sie aus der originalen aktuellen README;
keine Note vorgeben. Pilotwahl qwen-bildworkflow nur fuer AI-Tools-Short.
Business 37344290208: Story 7 bestanden, Bau am ersten Bild gesperrt.
Figurenpruefer bemangelte Handhaltung gegen Referenz; zweites Bild passte
nicht zur Handlung. Nun Objektaufnahme ohne erzwungene Figur im Hook;
Figur am Ende als Portrait ohne riskante Handpose. Abgelehnte Bilder werden
fuer echte Sichtkontrolle im privaten Pilot-Artefakt behalten, nie eingesetzt.
AI-Vorlage 37345221770: Groq beanstandete ungenaues "documentation offers
three things" (Quelle nennt vier Verbesserungen) und "developer examples"
als nicht ausdruecklich belegte Urheberschaft. Text jetzt unsere Auswahl von
drei Funktionen; keine pauschale Aussage ueber Urheberschaft der Bilder.
Zusatzbefund beim echten Qwen-Beispiel `example-04.png`: RGBA (684x685),
Alpha 0..255; naive RGB-Konvertierung zeigt verborgene magentafarbene Pixel.
Renderer/Beispielvorschau legt transparente Bereiche jetzt korrekt auf ein
Schachbrettraster, deckende Bildpixel bleiben erhalten. Eigener Regressionstest.
Telegram-Noten werden ausdruecklich als KI-Bewertung bezeichnet. Persistente
Lernregel gegen Parameter-/Architekturvortraege statt konkreten Nutzens.
AI-Lauf 37345853542: Fakten/Story 8 bestanden; erster Bildbau scheiterte
an tatsaechlich sichtbaren kuenstlichen Signaturen (lokal angesehen), keine
blinde Fehlablehnung. FLUX.2 Klein wird nun auch ohne Figurenreferenz im
ersten Versuch verwendet, mit multipart laut offizieller Cloudflare-Doku:
https://developers.cloudflare.com/workers-ai/models/flux-2-klein-4b/
Nur bei fehlendem/abgelehntem ersten Bild ohne Referenz ein begrenzter
FLUX.1-Zweitversuch; keine ungeprueften Bilder freigeben. Klarere leere
Bildraender und kuerzerer Prompt ohne Poster-Typografie-Anmutung.
Echter Telegram-Fehler: Nachricht "Es wurden einfach viel zu wenig Fotos
verwendet" lag faelschlich als Business-Thema in der Warteschlange. Gezielt
nach `lernen/telegram-feedback.json` uebernommen. Feedback-Praefix und klare
Videoqualitaetsbeschwerden erkennt `themen.ist_feedback` nun vor Themenwahl;
Originalwortlaut bleibt gespeichert, beide Kanaele/Planer/Pruefer erhalten
ihn. Fremde Chats und echte Themen bleiben getrennt. 146 lokale Tests bestanden.
Business 37345859195: Bildplan plante mehrere Archivfotos derselben Szene,
obwohl nur eines verfuegbar war; Bau stoppte in Phase 1, danach zweiter
Versuch wegen Bilddefekten. Planer jetzt explizit jedes echte Foto nur einmal;
fehlendes passendes Foto darf durch eine klar gekennzeichnete illustrative
Rekonstruktion ersetzt werden, nie durch leer/unpassend. Alle Illustrationen
auch im Business-Video sind gekennzeichnet. Native Pruefung summiert nun
benachbarte Slots mit gleichem Motiv: drei 4-s-Zooms sind weiterhin 12 s
Bildhaltezeit und gesperrt. 147 Tests inklusive dieser Umgehungsprobe bestanden.
Bildauftrag mit maximal langer Szene/Referenz/Korrektur zuvor 2122 Zeichen,
ueber dem FLUX.1-Limit 2048. Szenenbudget auf 500 Zeichen begrenzt; externer
API-Vertrag nun auch mit maximalem Input getestet (148 Tests insgesamt).
Aktuelle Piloten dc24187: AI 37347051952, Business danach 37347058003,
beide telegram=false. Bis zum Artefakt keine Zustellung behaupten.
AI 37347051952: Story 8, Bau bis zur Transparenzphase. Die automatische
Auswahl hatte die Benchmarkgrafik example-01 genommen und verweigerte
dann ein weiteres Beispiel. Reale Quellenbilder lokal kontrolliert: 04/05/06
sind Alpha-Ausgaben, 15 ist das Referenzgruppen-Beispiel; 01/43 sind fuer
diesen Workflow ungeeignete Diagramme. Nun redaktionelle `bildfolge` mit
geprueften Quell-URLs, nur akzeptiert wenn in Original-README vorhanden.
Gemini plant weiterhin den zeitlichen Schnitt, Vorgaben beruehren nie Ton.
Alle Tool-Ausgaben bekommen MODEL CARD EXAMPLE, konzeptionelle Szenen
ILLUSTRATION. Schluss kann die vorhandene originale Kanalfigur verwenden,
statt eine neue Identitaet zu erfinden. Vollstaendiger Plan nun als Artefakt
`bildplan.json` auch bei Bauabbruch. Neue Regressionen fuer Quellenbindung
und unveraenderten Sprechtext: insgesamt 150 lokale Tests bestanden.
Implementiert in `bildplan.py`: Originalton/Wortzeiten behalten, Phasen in
ca. 3-5-Sekunden-Einstellungen aufteilen, ein gebuendelter Gemini-Aufruf fuer
konkrete unterschiedliche Motive. Zoom, Ausschnitt oder Untertitelwechsel
zaehlen nicht als neue Motive. Native Bildpruefung: lueckenlose Abdeckung,
kein Hintergrund-only, hoechstens 6 s pro Short-Einstellung und mindestens
ein unterschiedliches Quelldatei-Motiv pro 7 Sekunden Gesamtdauer. Bei
einem 90-s-Short also mindestens 13 Motive, typischerweise 20-26 Einstellungen.
Langformat getrennt mit 8-s-Plan, 10-s-Grenze und einem Motiv pro 16 s.
Das sind redaktionelle Heuristiken, keine garantierte Zuschauerbindung.

Beide KI-Auftraege und Bildwahl erhalten feste Nutzerregeln; alte KI-Lernregeln
koennen diese Datei nicht loeschen. Keine genaue menschliche Note erfinden:
Feedback lautet <5, nicht exakt 4. Bilder groesser, Dauertitel nur im Einstieg
oder Tool-Platz, Foto selbst als weichgezeichneter Hintergrund statt Kerzen.
Unpassende/leere Bilder stoppen den Bau. Tool-Phasen verlangen echte
Beispielbilder aus der jeweiligen Quelle; fehlende Beispiele sind kein
Anlass fuer erfundene Outputs. Figurenidentitaet muss stimmen, Blickrichtung
und Pose duerfen sich aendern. Promptversion `2026-10-05.8`.

137 lokale Regressionstests bestanden; lokale Videoanalyse jetzt mit
`imageio-ffmpeg` unter ignoriertem `ausgabe/werkzeuge` moeglich. Neue echte
Piloten/Ergebnisse noch zu ergaenzen. Zunaechst ohne automatischen Telegram-
Versand bauen, echte Frames kontrollieren, dann `github_pilot.py senden RUN
KANAL` via `pilot-versand.yml`. Der Sender prueft erneut Fakten, Technik,
Noten und Nutzerablehnung. Nicht allein wegen einer KI-9 freigeben.

Auf Commit `006aff2` gestartet: AI Tools Explained
[37341670490](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37341670490)
und danach Business/Nintendo
[37341676776](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37341676776).
Beide `telegram=false`, damit echte Frames vor Zustellung kontrolliert werden.
CI [37341669860](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37341669860)
ist bestanden. Kein doppelter Start, solange diese Laeufe aktiv sind.
Zusaetzlich: lokale echte Kontaktboegen via `pruefungen/video_vorschau.py`;
Demo-Bilder ohne Dateisuffix als Standbild erkennen. Effekte bei Phasen-/
Handlungswechseln, nicht bei jedem einzelnen Bildwechsel vervielfachen.

Der Nutzer hat die Weiterentwicklung und echte Probelaufe autorisiert.
Gewuenscht sind bessere Prompts fuer Skript, Bild, Video, Stimme, Musik und
Geraeusche; ein lernfaehiges Tool; starke Zuschauerbindung von Anfang bis Ende
bei Shorts und Langvideos; professionelle Ergebnisse oberhalb von 8/10.
Spaetere ausdrueckliche Nutzerkorrektur: Versand ab 7/10 bis 10/10;
9/10 war als Mindestnote zu streng.
Bestandene Videos sollen samt Skript und Upload-Texten auf Telegram kommen.
Zusatzauftrag: alle neuen Aenderungen und den Betriebsstand fuer Claude
dokumentieren. Es ist keine automatische Plattform-Veroeffentlichung beauftragt.

### Verbindliche Gestaltungs- und Soundvorgaben des Nutzers

**Figuren und illustrierte Videogestaltung sollen GTA-maessig wirken**:
urbane, gemalte Comic-/Open-World-Spielplakat-Anmutung, klare markante
Konturen, realistische Proportionen, plastische Farbflaechen, cineastisches
Licht und ausdrucksstarke Perspektiven. Das ist eine allgemeine visuelle
Referenz, keine Aufforderung zu Kopien. Ausschliesslich eigene Figuren und
Kompositionen; keine GTA-Charaktere, charakteristischen Outfits, Logos,
Karten, konkreten Spielszenen oder nachgestellten Covermotive uebernehmen.
Die feste Kanalfigur muss zwischen Szenen wiedererkennbar bleiben und
darf nicht als echter historischer Gruender ausgegeben werden.
Echte Belegfotos und Demos bleiben unverfaelschte visuelle Belege.

**Hintergrundsound nicht vergessen:** Instrumentalmusik und Geraeusche sollen
zur konkreten Szene, Epoche, Stimmung und Erzaehlkurve passen. Neugier,
Spannung und Aufloesung erhalten passende, sparsame Akzente; keine beliebige
Dauermusik, kein pauschaler Action-/Gangster-Sound wegen des Bildstils.
Die Stimme bleibt verstaendlich; keine konkurrierenden Vocals, grellen
Whooshes oder abrupten Enden. Die fertige Tonspur tatsaechlich anhoeren.
Passung ist Teil der Video-Kritik und darf nicht bloss behauptet werden.
Aktuell wird ein ausgewaehltes Musikbett mit Stimme/Effekten gemischt;
automatischer Wechsel mehrerer Musikstuecke je Kapitel ist noch nicht
implementiert. Die konkrete Musikpassung muss der echte Pilot bestaetigen.

Eine Bewertung von 9/10 ist das Urteil der unabhaengigen KI-Pruefung.
Sie ist weder eine belegte Verbesserung der Zuschauerbindung noch eine
Garantie fuer Reichweite. Dafuer sind echte veroeffentlichte Videos und
ausreichende Analytics-Daten erforderlich.

### Verbindliche Aufforderung zum Liken, Teilen und Speichern

Neuer Nutzerauftrag: Jedes Video soll ausdruecklich zum **Liken, Teilen und
Speichern** auffordern. Alle drei Aktionen nennen; "follow/subscribe" allein
erfuellt die Vorgabe nicht. Shorts: einmal nach dem inhaltlichen Hoehepunkt
bzw. der Aufloesung, kurz vor Schluss. Langvideos: zweimal, am Anfang nach
Hook/erstem hilfreichem Kontext innerhalb der ersten 20–30 Sekunden und am
Ende nach der zentralen Aufloesung. Die erste Aussage bleibt der Story-Hook.
Jeweils eine kurze, natuerliche englische Zeile, moeglichst maximal 12 Woerter.
Zum Beispiel: "Like, share and save this story for later."
Praezisierung des Nutzers: Der Aufruf muss **immer tatsaechlich gesprochen**
werden, ausdruecklich und verbindlich: "Be sure to like, share and save this
video." (= "Unbedingt liken, teilen und dieses Video speichern.").
Nur eine Einblendung oder Beschreibung reicht nicht; kein optionaler oder
bedingter Aufruf. Die englische Kanalsprache bleibt erhalten.
Die Worte zaehlen zum Laengenbudget. Keine weiteren wiederholten Aufrufe.

Umgesetzt als gemeinsame Promptregel in `dramaturgie.interaktion()`,
verwendet von Skriptautor, Storypruefer und Video-Kritik sowie Doku-Editor.
Die alte Begrenzung auf hoechstens einen Save-/Follow-Aufruf ist entfernt;
Promptversion jetzt `2026-10-05.6`. Diese Vorgabe gilt fuer neu gestartete
Laeufe. Die bereits oben/unten dokumentierten Nintendo-Piloten sind auf
Commit `159009c` / Promptversion `.4` festgelegt und werden durch diesen
Commit nicht nachtraeglich umgeschrieben. Es werden keine echten Likes,
Shares oder Saves garantiert oder automatisch erzeugt.

## Tatsaechlicher Betriebsstand

- Workspace: `C:\Users\saima\Downloads\contentfabrik`.
- Privates Repository: `aKhaaaaaan/contentfabrik`, Standardbranch `main`.
- Der Windows Git Credential Manager hat einen bestehenden GitHub-Zugang.
  Lesen und Push sind erlaubt. In dieser Codex-Sandbox war der geschuetzte
  Speicher zunaechst unsichtbar; mit genehmigtem Zugriff funktioniert er.
  Die fruehere Aussage "kein nutzbarer GitHub-Zugang" ist damit ueberholt.
- GitHub-Secrets sind vorhanden: `GEMINI_API_KEY`, `GROQ_API_KEY`,
  `CLOUDFLARE_AI_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `PIXABAY_API_KEY`,
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `YOUTUBE_API_KEY`, `YT_CLIENT`,
  `YT_TOKENS`, `CLAUDE_CODE_OAUTH_TOKEN`. Nur Namen wurden gelesen, keine Werte.
- Lokal fehlen ffmpeg/ffprobe und die Produktionsmodelle. Die echten
  Produktionsversuche laufen auf GitHub Actions mit dessen Secrets.
- Beim ersten Live-Statusabruf liefen keine Video-Jobs mehr. Der vorher von
  Claude gestartete Business-Lauf `37291265520` war erfolgreich beendet:
  05.10.2026 09:37–09:57 UTC, also 11:37–11:57 Berlin.
  Link: https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37291265520
- Der aktuelle Business-Verlauf enthaelt ein FedEx-Video mit `status=gesendet`,
  Video-Note 8 und Story-Note 4. Es wurde nach den alten Regeln versendet.
  Das ist KEIN bestandener Versuch nach dem neuen Filter.
- Ein gruener GitHub-Status allein bedeutet nicht, dass ein Video die
  Qualitaetspruefung bestanden hat oder auf Telegram angekommen ist.
- `git fetch origin` und `git merge --ff-only origin/main` haben die beiden
  neuen Verlaufs-/Lern-Commits `58db90a` und `750421d` erhalten. Sie wurden
  nicht durch die lokalen Codeaenderungen ersetzt.
- Das Skydance-Video aus der alten Sitzung war nur ein Vergleichsentwurf.
  Nicht als fertig oder zur Veroeffentlichung freigegeben behandeln.

### Echte neue Piloten

Gestartet am 05.10.2026 um 13:42 UTC / 15:42 Berlin mit Code-Commit
`159009c` und `telegram=true`: jeweils Nintendo fuer Business Origin Stories,
um dieselbe belegte Geschichte in beiden Formaten vergleichen zu koennen.

| Lauf | ID / Link | Zuletzt bestaetigter Status |
|---|---|---|
| Code-/Regressionstest | [37318832824](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37318832824) | erfolgreich, neue Pruefungen bestehen auch auf Linux |
| Short | [37318880596](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37318880596) | gesperrt: Faktenpruefung nicht bestanden; kein Video gebaut/gesendet |
| Langvideo | [37318886482](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37318886482) | gesperrt: Story 6/10; kein Video gebaut/gesendet |

Nicht erneut starten, ohne diese Run-IDs zu kontrollieren. Erst mit fertigem
Pruefbericht und erfolgreichem Telegram-Schritt von einem zugestellten
bestandenen Video sprechen. Neue Status-/Ergebnisdetails werden unten ergaenzt.

### Ausbleibende Telegram-Nachricht: Ursache und Korrektur

Am 05.10.2026 meldete der Nutzer, dass keine Telegram-Nachricht angekommen
sei. Beide Piloten waren inzwischen fehlgeschlagen, VOR dem Videobau:

- Short: 471,9 Sekunden Produktionszeit; Faktenpruefung abgelehnt, Story
  deshalb noch nicht bewertet. Beanstandet wurden unter anderem spekulative
  Formulierungen/Illustrationsbeschreibungen und unbelegte Kausalitaet.
- Langvideo: 982,9 Sekunden; Faktencheck formal bestanden, Story 6/10,
  Hook 5/10. Die Themenwahl wechselte trotz Nintendo-Vorgabe zu Apple.
  Diese Abweichung ist ein noch offener Fehler der Themen-/Historienprioritaet.
- Beide verwendeten zuletzt `gemini-flash-lite-latest`. Das allein belegt
  weder die Ursache schlechter Qualitaet noch ein bestimmtes Kontingentproblem.
- Die alten Pilotlaeufe unterdrueckten alle internen Telegram-Meldungen
  (`CF_PILOT=1`); der separate Versand war nur bei Erfolg erlaubt. Darum
  kam zu den Fehlversuchen ueberhaupt keine Nachricht. Kein bereits fertiges
  Video wurde auf Telegram verloren.

Korrektur: `fabrik/statusmeldung.py` sendet bestaetigte Statusmeldungen ohne
KI-Aufruf und ohne Video-Freigabe. Bei `telegram=true` bestaetigt `pilot.yml`
den Start VOR Einrichtung/Produktion. Ein separates Fehlerjob meldet danach
Abbruch oder Fehlschlag mit dem berichteten Grund, auch wenn der Hauptjob
sein Zeitlimit erreicht. Nach bereits bestaetigtem Videoversand wird keine
irrefuehrende "kein Video"-Fehlermeldung erzeugt.

`lauf.py` speichert jetzt Exitcode, konkrete Skript-Sperrgruende, Story-Note
und Faktenprobleme im Bericht. `pruefungen/github_pilot.py` verwendet UTF-8
fuer die Windows-Ausgabe; Emojis in Cloud-Logs hatten zuvor den Abruf des
Short-Fehlerauszugs mit einem UnicodeEncodeError unterbrochen.

`.github/workflows/telegram-status.yml` erlaubt eine manuell ausgeloste
Statusnachricht an den bestehenden Chat mit den vorhandenen GitHub-Secrets;
kein neuer Videobau. Lokaler Aufruf: `python pruefungen/github_pilot.py melden
ausgabe/pilot-status.txt`. Es werden keine Keys lokal kopiert.

Echter Verbindungstest bestanden am 05.10.2026 um 14:46:20 UTC / 16:46 Berlin:
[Telegram-Statuslauf 37327384289](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37327384289).
Telegram bestaetigte `ok=true`; der Log zeigt `message_id: 108`. Die Nachricht
erklaert beide gesperrten Piloten und die korrigierte Rueckmeldung. Dies
bestaetigt den Versand an den hinterlegten Chat, nicht dass der Nutzer die
Nachricht bereits gelesen hat, und ist kein bestandener Video-Pilot.
Die Cloud-Regression des Fixes besteht ebenfalls:
[Pruefung 37327344050](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37327344050).

## Qualitaetsfilter und begrenzte Nachbesserung

`fabrik/qualitaet.py` ist die gemeinsame Freigabestelle fuer den normalen
Lauf und den direkten Telegram-Aufruf:

- Story und Video jeweils mindestens **7/10**, auf aktuellen Nutzerwunsch.
- Alle erforderlichen Einzelkategorien mindestens **7/10**, nur die unsichere
  Story-Teilbarkeitsprognose mindestens **6/10**.
- Story: Hook, Spannung, Ueberraschung, Tempo, Aufloesung, Teilbarkeit.
- Video: Hook, Bildpassung, Dynamik, Text, Ton/Stimme, Tempo, Inhalt,
  Schluss/Loop, Regeln, Story.
- Faktenfreigabe muss exakt `ok=true` sein; fehlende oder ungueltige
  Bewertungen und Messwerte bestehen nicht.
- Technik muss gemessen sein und darf keine Befunde enthalten.
- Offene mittlere/schwere Probleme sperren auch ein Video mit hoher Gesamtnote.
- Bei gleicher Gesamtnote wird der ausgewogenere bestandene Kandidat behalten.
  Eine misslungene Korrektur ersetzt kein bereits bestandenes Video.

`fabrik/budget.py` speichert ein Tagesbudget je Kanal und UTC-Tag.
Mehrere Zeitfenster teilen insgesamt 30 Minuten Produktionszeit. Vor Beginn
wird reserviert; normales Ende gibt Restzeit zurueck, ein harter Abbruch
behaelt die Reservierung. Keine unbegrenzten Wiederholungen nach Fehlern.

`fabrik/lauf.py` versucht maximal fuenf Runden und hoechstens zwei gezielte
Korrekturen desselben Videos. Es behaelt Reserve fuer Korrektur/Zustellung,
speichert jeden Versuch und liefert im Pilot bei fehlendem bestandenen
Video einen Fehlercode statt eines irrefuehrenden Erfolgs.

`fabrik/nachbessern.py` erstellt einen begrenzten Reparaturplan zu konkreten
Problemen/Zeitstellen. Nur erlaubte Aenderungsarten werden ausgefuehrt;
Textaenderungen brauchen erneut Fakten- und Storypruefung. Keine Reparatur
darf erfundene Motive, Zitate, Ursachen oder neue unbelegte Zahlen einfuehren.

## Skripte, Prompts und Dramaturgie

Die gemeinsamen Prompts liegen in `fabrik/prompts.py`; ihre Fassung ist
`2026-10-05.5`. Details und providerbezogene Regeln stehen in `PROMPTS.md`.
Skript, Faktenpruefung, Storypruefung, Bildpruefung und Video-Kritik benutzen
getrennte Aufgaben mit konsistenter Bewertung. Die Video-KI bekommt keine
alte Story-Note als Vorgabe fuer ihr Urteil.

- Ein klarer zentraler Gedanke und eine beantwortete Leitfrage.
- Der erste Frame zeigt bereits Thema/Problem; kein langes Logo-Intro.
- Jeder Abschnitt liefert neue Information, Beleg oder eine Konsequenz.
- Kleine Aufloesungen waehrend des Videos; nicht alle Antworten bis zum
  Ende zurueckhalten, keine leeren Teaser oder erfundene Dramatik.
- Quellengebundene Aussagen, korrekte Zahlen und Vergleiche; keine frei
  erfundenen Erfolgsgeschichten, Motive oder Dialoge.
- Bildwechsel folgen dem Inhalt; wichtige Erkenntnisse duerfen wirken.
- Modelltemperaturen, Bild-MIME-Typen und Requests beachten die jeweiligen
  Modellvertraege; Ausfaelle fuehren nicht zu erfundenen Freigaben.

`fabrik/dramaturgie.py` unterscheidet `videoformat=short|lang` und validiert
`laenge_s`. Defaults: Short 62–90 Sekunden, Langvideo 360–600 Sekunden.
Shorts duerfen mit diesem Profil maximal 180 Sekunden lang sein.

Fuer Langvideos: 3–5 Kapitel, 24–50 sinnvolle visuelle Beats, lokale Fragen
und Aufloesungen, gelegentliche hilfreiche Zusammenfassung, klares Ende
ohne langes Outro. Kein durchgehender Shorts-Hektikmodus.

Optional im Skript: `beat`, `bildmodus` und `bildtext`. Bildtext ist nur eine
wirklich gesprochene, zusammenhaengende Phrase aus 2–5 Woertern mit maximal
26 Zeichen. Anzeige folgt den Wortzeiten; maximal jeder zweite Abschnitt.
Keine geratenen Zeitpunkte oder frei erfundenen Einblendungen.

`fabrik/skript.py` braucht fuer Langvideos ausfuehrlichere Quelltexte und
passende Wortzahl/Sprechgeschwindigkeit. Die Storypruefung erfolgt vor
dem aufwendigen Render. Der alte Doku-Editor `fabrik/doku.py` bleibt ein
separater Kapitel-Skripteditor; seine Datei ist kein direktes Rendererformat.
Auch er hat jetzt die strengere Story- und Wortzahlpruefung.

## Bild, Schnitt, Untertitel und Ton

`fabrik/bauen.py` rendert je nach Format:

- Short: 1080 × 1920, sichere Positionen fuer Titel, Bild und Untertitel.
- Langvideo: 1920 × 1080, grosses Bild links und gelegentliche kurze Details
  rechts; eigene Titel-/Kapitel- und Untertitelpositionen.
- Fotos/Demos bleiben voll sichtbar statt wichtige Bildteile abzuschneiden.
  Stockclips koennen passend beschnitten werden; echte Demo-Texte werden
  nicht durch unruhige Zooms zerstoert.
- Sanfte, begruendete Bewegung statt periodischer harter Zoomschlaege.
- Wortgruppen werden nach Schriftbreite umgebrochen; ASS-Inhalte bereinigt;
  lange Sprechpausen bleiben frei von haengenden Untertiteln.
- Lange Videos bekommen sparsame Uebergangstoene an Kapitelwechseln und
  Wendungen; Musik wird unter die Stimme abgesenkt und sauber eingeblendet.
- `fabrik/ton.py` passt Tempo anhand tatsaechlicher Sprechdauer an;
  neue Synthese nur wenn erforderlich, innerhalb enger Formatgrenzen.

`fabrik/illustration.py` prueft erzeugte Szenen vor Einsatz, behandelt
Ausfaelle begrenzt und achtet auf Format/Referenzgroesse und die Parameter
der vorhandenen Cloudflare-Modelle. Ein verworfenes Bild wird nicht trotzdem
eingebaut. Illustrationen sind keine historischen Beweisfotos.

`fabrik/rendercache.py` erkennt Aenderungen an Text, Darstellung, Prompts,
Tonregeln und Renderer. Unveraenderte Stimmen/Abschnitte/Clips koennen
wiederverwendet werden; geaenderte Teile werden neu gebaut.

`fabrik/kritik.py` misst Aufloesung, Laenge, Framerate, H.264/AAC, 48-kHz-
Stereoton und Lautheit um -14 LUFS. Erst danach geht das vollstaendige
Video mit Ton an Gemini zur redaktionellen Pruefung. Keine reine Stichprobe.
Hochgeladene Pruefdateien werden danach entfernt.

Artefakte: `skript.json`, `quellen.json`, `messung.json`, `dramaturgie.json`,
`kritik.json`, `korrektur.json`, `bericht.json`, `untertitel.ass` und Video.
Aus Kompatibilitaetsgruenden heisst auch das Langvideo **`short.mp4`**.
Das Format steht in `skript.json`; nicht aus dem Dateinamen ableiten.

## Lernen aus echten Ergebnissen

`fabrik/lernen.py` speichert Ausgangs-/Ergebnisnoten, Korrekturart, Aufwand
und Auswertbarkeit. Neue technische Fehler oder offene schwere Probleme
zaehlen nicht als Verbesserung. Eine fehlende Pruefung liefert kein
positives Lernsignal. Regeln werden begrenzt und zusammengefuehrt.

`fabrik/erfolg.py` trennt Shorts und Langvideos in Vorbildern/Einstellungen.
YouTube-Kurven werden erst fuer oeffentliche Videos ab 48 Stunden und
mindestens 100 Aufrufen ausgewertet. Erneut abrufen bei 50 % Wachstum oder
nach sieben Tagen. Lokale Verluste brauchen zwei bestaetigende Messpunkte;
keine Schlussfolgerung aus einem Ausreisser oder dem normalen Videoende.
Das sind interne Heuristiken, kein statistischer Wirksamkeitsnachweis.
Ein Kurvenknick allein erklaert nicht seine Ursache.

## Telegram und Cloud-Workflows

`fabrik/freigabe.py` prueft den gemeinsamen Filter erneut, auch beim direkten
Aufruf. Es sendet Video, Pruefhinweise, vollstaendiges Skript und Upload-Texte.
Lange Texte/Quellenangaben werden verlustfrei geteilt. Langvideos bekommen
weder `#shorts` im Titel noch einen unpassenden TikTok-Uploadtext.
Zu grosse Dateien werden als Telegram-Kopie komprimiert; im Cloud-Pilot
fuehrt ein Begleitlink zum privaten Artefakt mit dem Original in voller
Qualitaet. Die KI-Note bezieht sich auf das gepruefte Original, nicht auf
einen gesondert bewerteten Telegram-Kompressionsdurchlauf.

- `.github/workflows/video.yml`: Produktionszeitplan, offene Kanaele,
  gemeinsame dauerhafte Budgets, Telegram und Sicherung von Verlauf/Lernen.
- `.github/workflows/themen.yml`: Themenabholung; teilt die Warteschlange
  mit den schreibenden Produktionslaeufen.
- `.github/workflows/pilot.yml`: echter manueller Probelauf mit `kanal`,
  `videoformat`, optionalem `thema`, optional `telegram` (Standard false).
  Bei Telegram-Auswahl werden dessen Secrets vor Produktionsbeginn geprueft.
  Versand erfolgt erst nach erfolgreichem Bau/Pruefung und Artefakt-Sicherung.
  Kein Plattform-Upload und kein Push von Pilot-Zustandsdateien nach `main`.
- `.github/workflows/pruefen.yml`: Python-Regressionen, Syntax und Zeitplantest
  bei Code-/Workflow-Aenderungen.
- `formate/business-origin-stories.json`: optionales 6–8-Minuten-Langprofil,
  nicht automatisch in den taeglichen Shorts aufgenommen.
- `pruefungen/github_pilot.py`: fester Repositoryzugriff ueber gespeicherten
  Credential-Manager-Zugang. Befehle `status`, `secrets` (nur Namen),
  `details <run>`, `download <artifact>`, `dispatch <kanal> <short|lang>`
  mit optional `--thema` und `--telegram`. Kein Token im Log oder Dateisystem.
  Bei Download-Weiterleitungen wird der GitHub-Authorization-Header entfernt,
  sobald der Zielhost wechselt; unverschluesselte Weiterleitungen werden
  abgelehnt. Drei Regressionstests pruefen diese Zugangsdaten-Grenze.
  Laufende Joblogs sind derzeit per API noch nicht verfuegbar; `details`
  zeigt dann die tatsaechlichen Schrittstatus statt erfundener Fortschrittswerte.

Wichtig: Pilotdateien liegen drei Tage als private GitHub-Artefakte.
Lernen/Budget im Pilot werden NICHT automatisch in den Betrieb uebernommen.
Getrennte Cloud-Checkouts teilen dieses Pilotbudget nicht dauerhaft;
das ist fuer die begrenzten manuellen Vergleichslaeufe vorgesehen und
kein Mechanismus fuer unbegrenzte Ersatzstarts.

### Cloudflare-Zeitplan und vom Nutzer erstellter PAT

`cloudflare/zeitplan-worker.js` ist vorhanden und lokal mit fuenf Faellen
geprueft. Er startet `video.yml` mit `kanal=alle` bzw. `themen.yml` ueber
GitHub `workflow_dispatch`. Geplante UTC-Crons: `23 8 * * *`, `41 10 * * *`,
`23 13 * * *`, `41 15 * * *`; Themen: `7 */4 * * *`.

Der Nutzer schrieb, dass er den eng begrenzten GitHub-PAT bereits erstellt
hat. Der alte Claude wollte danach den Worker im Cloudflare-Browser anlegen.
**Ein fertig eingerichteter oder aktiver Cloudflare-Cron wurde in dieser
Sitzung nicht bestaetigt.** Den Worker nicht als deployed bezeichnen.
Es gibt hier keinen angebundenen Cloudflare-Browser/Verwaltungszugang.
Der GitHub-Zugang im Credential Manager ersetzt NICHT den Worker-Secret.
Der vorhandene AI-Token ist ebenfalls keine bestaetigte Worker-Deployment-
Berechtigung. PAT nicht nochmals erstellen lassen und nicht im Chat anfordern.
Im Dashboard muss er als verschluesseltes Worker-Secret **`GH_TOKEN`**
hinterlegt werden, beschraenkt auf dieses Repository und Actions Read/Write.
Anschliessend Cron-Ausfuehrung und GitHub-Dispatch wirklich kontrollieren.

Die konkrete Eingabestelle fuer den bereits erstellten Token ist:
Workers & Pages → Worker auswaehlen → Settings → Variables and Secrets →
Add → Typ **Secret**, Name **GH_TOKEN**, Value = vorhandener PAT → Deploy.
Quelle: [Cloudflare, Secrets im Dashboard](https://developers.cloudflare.com/workers/configuration/secrets/).
Crons: Worker → Settings → Triggers → Cron Triggers;
Quelle: [Cloudflare, Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/).
Ein Aufruf der Worker-Statusseite startet keinen Job und beweist weder
funktionierenden PAT noch aktiven Cron. GitHub-Run und Cron Events pruefen.

## Pruefungen und Grenzen

Lokal bestanden nach den Telegram-Erweiterungen:

```powershell
python -m unittest discover -s pruefungen -p test_*.py
node --test pruefungen/zeitplan.mjs
git diff --check
```

Ergebnis nach Statusmeldungen und redaktionellem Pilot: **129 Python-Tests**,
**5 Zeitplan-Prueffaelle**, keine Diff-Fehler.
Python-/Node-Tests benutzen Ersatzantworten; kein echter Telegram-Versand,
keine Modellgenerierung und kein echter ffmpeg-Render in den Tests.
Die Tests belegen Ablauf/Sperren, nicht die Wirkung fertiger Videos.

`pruefungen/gestaltung_vorschau.py` hat Layout-Vorschauen mit einem
gecacheten Foto erzeugt: `ausgabe/gestaltung/short-layout.png` und
`lang-layout.png`. Sie wurden visuell kontrolliert, sind aber keine
fertigen Videos und bilden den echten ASS-/ffmpeg-Lauf nicht vollstaendig ab.

Der Short-Pilot unten bestaetigt jetzt echten Render, KI-Pruefung mit Ton,
eine gemessene Bildkorrektur und Telegram-Zustellung. Noch tatsaechlich zu
pruefen: Langvideo, persoenliche Sicht-/Hoerabnahme und Kompressionsqualitaet.
Bei API-Kontingentproblemen Ursache dokumentieren statt Schwellen absenken.

## Dokumentation und sinnvolle Fortsetzung

### Gezielter Ersatzpilot: Nintendo-Karten

Stand vor den neuen Ersatzpiloten: Der Nutzer hatte kein Video erhalten;
`message_id:108` bestaetigt
nur eine Statusnachricht. Beide bisherigen neuen Piloten scheiterten vor
dem Render. Nicht als Videozustellung darstellen.

Neu vorbereitet: `piloten/nintendo-karten.json`, ein redaktioneller Short
mit 185 Woertern aus dem gespeicherten Nintendo-Quelltext. Schwerpunkt:
teure, langlebige Karten, die guenstigere Tengu-Linie und spaetere neue
Zielgruppen. Keine erfundene Krise oder vorgegebene Story-Note.
`pilot.yml` und `github_pilot.py dispatch` verstehen
`--entwurf nintendo-karten`, nur fuer Business/Short. `pilot_entwurf.py`
entfernt alte Pruefungen und prueft Fakten, Zahlen, Groq und Story wirklich
neu. Das unveraenderte gesperrte Skript wird nicht fuenfmal erneut bewertet.
Der normale Renderer, Video-Kritik, Korrekturen und Telegram-Gate gelten.
Gestartet auf Commit `fca972f` mit der damaligen 9/10-Grenze:
[Pilot 37329938782](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37329938782).
Ergebnis: Faktencheck sperrte die Formulierung "Improving quality wasn't
the only answer ..." als widerspruechlich zur guenstigeren, niedrigeren
Qualitaet. Es wurde keine Videodatei gerendert. Artefakt `11354306858` lokal
heruntergeladen. Diese doppeldeutige Formulierung wurde durch eine explizite
Aussage ueber geringere Qualitaet und Preis ersetzt, danach neuer Start.

Danach verlangte der Nutzer ausdruecklich 7/10 bis 10/10 und einen neuen
Telegram-Versuch. Zentrale Mindestnote und Kategorienminimum jetzt 7;
Fakten, Technik und offene mittlere/schwere Probleme bleiben Sperren.
8/10 ist eine Empfehlung fuer die manuelle Veroeffentlichung, keine
Versandsperre. Bewertungen werden nicht umgeschrieben, die Pruefnotenskala
bleibt gleich. Alte auf 9/10 gestartete Runs aendern sich nicht durch Push.

Neuer 7/10-Pilot:
[37331157176](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37331157176),
Commit `8f2001c`. Beide Faktenpruefer bestanden (Gemini und Groq GPT-OSS-120B).
Story 7/10: Hook 8, Spannung 7, Ueberraschung 8, Tempo 7, Aufloesung 8,
Teilbarkeit 6. Daher noch kein Render; Kategorienminimum bleibt 7.
Artefakt `11354845584`. Konkrete Kritik: ein Satz wiederholt nur die
Schwierigkeit. Daraufhin diesen Satz durch die Bedeutung fuer Wiederkaeufe
ersetzt und Schluss auf das Anfangsmotiv langlebiger Karten zurueckgefuehrt.
Aktuelle Vorlage: 197 gesprochene Woerter.
Lauf auf Commit `a01bf7e`:
[37331710289](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37331710289).
**Ergebnis: bestanden und tatsaechlich auf Telegram gesendet.**
Der Versand-Schritt endete erfolgreich am 05.10.2026 um 15:35:49 UTC
(17:35 Uhr Berlin), Log `Gesendet: True`. `freigabe.telegram` verlangt fuer
jeden API-Aufruf, einschliesslich `sendVideo`, exakt `ok=true`; andernfalls
waere der ganze Schritt fehlgeschlagen. Das ist die erste bestaetigte
Videodatei dieser Sitzung, nicht nur eine Statusnachricht. Eine Video-
message_id wurde in diesem alten Checkout noch nicht protokolliert.

Artefakt `11355841542` heruntergeladen unter
`ausgabe/github/11355841542/ausgabe/`: MP4 mit 23.559.712 Bytes, 89,7 Sekunden,
30 FPS, -14,1 LUFS, keine Technikbefunde. Skript 8/10, Faktencheck und Groq
bestanden; Video zuerst 8/10, danach 9/10. Video-Kategorien mindestens 9,
keine offenen Probleme. Modell der Video-Kritik: `gemini-flash-lite-latest`.
KI-Urteil, keine persoenliche Sicht-/Hoerabnahme oder Analytics-Garantie.

Echte gezielte Korrektur: unpassendes Kerzenbild im Hook erkannt und durch
ein Foto ersetzt. Nur ein Abschnitt neu gebaut, sieben wiederverwendet;
Kritik 8 → 9, Bildpassung 8 → 9. Produktion insgesamt 964 Sekunden; Erstbau
558 Sekunden, Teilbau 183 Sekunden plus Pruefungen. Lernen im Pilot bleibt
privates Artefakt und wurde nicht automatisch in den normalen Betrieb kopiert.
Zwei KI-Illustrationen sind im Quellenverzeichnis enthalten. Kein Musik-
Quelleneintrag vorhanden: kein nachweisbares heruntergeladenes Musikbett;
12 Effekte laut Messung. Passende Hintergrundmusik bleibt deshalb gezielt
zu verbessern, obwohl die KI Ton/Stimme mit 9 bewertete.

Der Telegram-Sender protokolliert jetzt nach erfolgreichem `sendVideo` die
`message_id` der Videodatei. Der GitHub-Helfer zeigt diese Logzeile an.
Diese Erweiterung aendert kein Qualitaetsurteil und sendet selbst nichts.
Lokal bestanden: 42 Betriebs-/Versandtests nach dieser kleinen Logerweiterung;
129 Gesamttests nach Umstellung der Mindestnote. Tests benutzen Ersatzantworten.

Faktencheck-Fehler behoben: illustrative Szenen/Suchbegriffe werden nicht
mehr als gesprochene historische Behauptungen geprueft; Titel und Beschreibung
bleiben enthalten. Visuelle Passung wird weiter geprueft. Beanstandete
Klauseln und Zweitpruefung werden gespeichert statt nur eines Sammelfehlers.
Story-Pruefung bekommt auch den Titel im Renderer-Format. Gemini ueberspringt
im selben Prozess zuvor mit 404 abgelehnte Modelle bzw. nachgewiesen leere
Tageskontingente; 503 wechselt sofort zum naechsten Modell. Das belegt keine
aktuelle Ausschoepfung eines bestimmten Modells und senkt keine Schwellen.

`README.md` beschreibt Einrichtung und heutigen Funktionsumfang;
`PROMPTS.md` die Prompt-Aenderungen. `KONZEPT.md`, `ANLEITUNG-YOUTUBE.md`,
`GOOGLE-ANTRAG.md`, `TIKTOK-ANTRAG.md` und `sfx/LIZENZ.md` wurden um den
aktuellen Umfang und belegte Einschraenkungen ergaenzt. Historische
Antrags-/Messangaben wurden als Historie erhalten. Die Plattform-Audit-
Fragen sind nicht durch diese Codeaenderung geloest.

Als Naechstes die unten nachgetragenen echten Pilot-Ergebnisse lesen;
keinen doppelten Start ausloesen, solange schon ein passender Lauf existiert.
Gesperrte Entwuerfe anhand der konkreten Gruende verbessern, ohne Noten zu
manipulieren. Ein Dashboard und automatische Plattform-Uploads sind
weiterhin zukuenftige Arbeit, kein fertig vorhandenes Produkt.
