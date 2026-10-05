# Technische Umsetzung und Testnachweise fuer Claude

Stand: 05.10.2026. Neueste fachliche Vorgaben stehen in [CLAUDE.md](CLAUDE.md)
und [UEBERGABE-CLAUDE.md](UEBERGABE-CLAUDE.md). Dieses Dokument beschreibt
die gebauten Erweiterungen, ihre Dateien und die tatsaechlichen Pruefungen.

## Ergebnis und aktuelle Ziele

Beide neuen Shorts wurden gebaut, anhand echter MP4-Frames kontrolliert,
auf Telegram zugestellt und vom Nutzer als deutlich besser bestaetigt.

| Kanal | Geliefert und gemessen | Neues Planungsziel fuer vergleichbare Shorts |
|---|---|---|
| AI Tools Explained | 82,2 s, 23 Einstellungen, 12 unterschiedliche Motive | Etwa 14-18 passende, unterschiedliche Motive |
| Business Origin Stories | 89,7 s, 24 Einstellungen, 14 unterschiedliche Motive | Etwa 24 Einstellungen mit 18 passenden, unterschiedlichen Motiven |

Qualitaetsziel weiterhin 10/10. Tatsaechliche KI-Noten beider Videos sind 8/10;
der Nutzer hat keine numerische Note vergeben. Die neuere Business-Vorgabe
24/18 ersetzt die fruehere Empfehlung, 24/14 beizubehalten. Ist-Zahlen,
positive Rueckmeldung und das abgelehnte fruehere Video bleiben erhalten.

## Gebaute und erweiterte Bausteine

| Baustein / Dateien | Umsetzung und Zweck |
|---|---|
| [bildplan.py](fabrik/bildplan.py) | Trennt Sprechphasen von visuellen Einstellungen: mehrere passende Bilder je Phase, mit unveraendertem gesprochenem Text und Wortzeiten. Automatische Gemini-Planung bekommt Quellen, kanalspezifische Bibliothek und Nutzerfeedback. Vollstaendige redaktionelle Regie wird direkt benutzt; zu kurze Vorgaben stoppen. |
| [bauen.py](fabrik/bauen.py) | Verarbeitet den Bildplan, rendert kurze Einstellungen und fuehrt sie mit Stimme/Untertiteln zusammen. Hauptbilder sind gross sichtbar; fehlendes Material wird nicht durch Kerzen oder unpassende Hintergruende ersetzt. Illustrationen bekommen Kamerabewegung und Herkunftslabel. Figurenreferenzen lassen sich auch waehrend des Verlaufs verwenden. |
| [bibliothek.py](fabrik/bibliothek.py) | Neues Laden eigener sichtgepruefter Illustrationen ueber feste IDs. Kanal, Dateipfad und SHA256 muessen passen. Unbekannte IDs, andere Kanaele, Pfadausbruch, fehlende oder veraenderte Dateien werden abgewiesen. Der Modus `asset` braucht keine neue Cloudflare-Generierung. |
| [Bildbibliothek](assets/illustrationen/katalog.json) | 16 neue Originalillustrationen mit built-in image_gen erzeugt und visuell kontrolliert: sechs AI- und zehn Business-Motive. Darunter eigene Handlungsszenen mit beiden bestehenden Kanalfiguren. Katalog speichert Herkunft, Motiv, Kanal, Datei und Hash. |
| [pilot_bildregie.py](fabrik/pilot_bildregie.py), [Pilotvorlagen](piloten/) | Konkrete Bildfolgen fuer Qwen-Workflow und Nintendo-Karten. Originale Figur am Einstieg und wiederkehrend im Verlauf; Gegenstaende, Handlungen, Vergleiche und echte Beispiele dazwischen. Die vier Qwen-Demos werden jeweils einmal verwendet. |
| [infografik.py](fabrik/infografik.py) | Eigene lesbare Vergleichsgrafiken fuer die belegte Nintendo-Kartengeschichte: langlebige/guenstigere Karten und qualitative Preisrichtung. Keine erfundenen Preiszahlen oder historischen Fotos. Der Renderer beschraenkt diese Grafiken auf das passende Thema. |
| [illustration.py](fabrik/illustration.py) | Cloudflare-Bildgenerierung mit optionaler originaler Figurenreferenz und Bildpruefung. FLUX.2 verwendet multipart auch ohne Referenz; Referenz fuer den Versand verkleinert, Original erhalten. Promptlaenge begrenzt; verworfene Bilder werden zur Diagnose gespeichert. |
| Echte Demos in [bauen.py](fabrik/bauen.py) | Beispielbilder muessen aus der konkreten primaeren README stammen. Redaktionell ausgewaehlte URLs werden gegen diese Quelle geprueft. Unpassende Qwen-Benchmark-/Chartbilder ausgeschlossen. Transparente Bilder korrekt zusammengesetzt; extensionlose Bilddateien als Standbilder behandelt. Illustrationen sind keine behaupteten echten Tool-Ergebnisse. |
| [trends.py](fabrik/trends.py), [skript.py](fabrik/skript.py), [prompts.py](fabrik/prompts.py) | Primaere Beschreibungen statt allein Likes/Downloads oder technische Metadaten fuer den Nutzen. Begrenzte Quellenanreicherung; keine Vermischung verschiedener Ranking-Kennzahlen. Prompts fuer Fakten, Story, Bildregie und Kritik verbessert; Version `2026-10-05.9`. Gemeinsame Quellen-/Feedback-Regeln. |
| [ton.py](fabrik/ton.py) und Tonmix in [bauen.py](fabrik/bauen.py) | Natuerliche TTS-Grenzen, passende Pausen und Wortzeiten. Eigenes Instrumental als Rueckfall bei fehlender Musikquelle: 80 BPM Business / 100 BPM AI, ohne fremde Samples. Musik-Fades, Absenkung unter der Stimme, gezielte Soundeffekte und Lautheitsnormalisierung. Effekte orientieren sich an Erzaehlphasen statt jedem Bildwechsel. |
| [lernen.py](fabrik/lernen.py), [redaktion.json](lernen/redaktion.json) | Dauerhafte Nutzerregeln erreichen Autor, Bildplaner und Kritiker. Wortgetreue Kritik/positive Rueckmeldung an konkrete Video-Hashes gebunden. Urspruenglich abgelehnte MP4 bleibt gesperrt. Kanalziele AI 14-18 und Business 24/18 jetzt im wirksamen Lernstand gespeichert. |
| [themen.py](fabrik/themen.py), [Telegram-Feedback](lernen/telegram-feedback.json) | Qualitaetskritik aus Telegram als Feedback erkennen und speichern, statt sie versehentlich als neues Videothema einzuplanen. Nachrichten deduplizieren; passende Rueckmeldungen erreichen die Redaktionsregeln. |
| [kritik.py](fabrik/kritik.py), [qualitaet.py](fabrik/qualitaet.py) | Fertige MP4 wird redaktionell und technisch geprueft. Native Bildkontrolle: volle Abdeckung, keine Luecken, begrenzte Haltezeiten und echte unterschiedliche Material-Hashes. Zoom/Zuschnitt/Untertitel erzeugen keine neuen Motive. Nutzerablehnung hat Vorrang vor einer hohen KI-Note. |
| [rendercache.py](fabrik/rendercache.py), [nachbessern.py](fabrik/nachbessern.py) | Gezielte Korrekturen und Wiederverwendung passender Bauabschnitte. Bildaenderungen koennen den Ton erhalten; geaenderter Text invalidiert ihn. Signaturen beruecksichtigen Regie, Code und Bibliothekskatalog, damit alte Bilder nicht unbemerkt zurueckkehren. |
| [freigabe.py](fabrik/freigabe.py), [statusmeldung.py](fabrik/statusmeldung.py) | Versandpruefung mit Fakten-/Story-/Video-/Technikbefunden und Ablehnungssperre. Videonachricht erst nach Telegram-API-Erfolg bestaetigen; Skript und komplette Uploadtexte anschliessend senden. KI-Note explizit als solche kennzeichnen. Start-/Fehlermeldung ersetzt keine Videodatei. |
| [pilot.yml](.github/workflows/pilot.yml), [pilot-versand.yml](.github/workflows/pilot-versand.yml), [github_pilot.py](pruefungen/github_pilot.py) | Reproduzierbare private Produktionslaeufe, Artefakte zum Kontrollieren und separater Versand eines bereits kontrollierten Ergebnisses. Sicheres Herunterladen/Entpacken; keine GitHub-Autorisierung an fremde Redirect-Ziele weitergeben. |
| [video_vorschau.py](pruefungen/video_vorschau.py), [bericht.py](fabrik/bericht.py) | Kontaktbogen aus echten MP4-Frames zur Sichtkontrolle; Produktionsbericht mit gemessenen Zeiten, Noten und konkreten Sperrgruenden. |

Die vorhandenen externen Bibliotheken/Modelle, etwa Kokoro, Whisper, Pillow
und FFmpeg, wurden integriert bzw. weiterverwendet; sie wurden nicht selbst
entwickelt. Die Cloudflare-Zeitplanung stammt teilweise aus der uebernommenen
Vorarbeit; [zeitplan.mjs](pruefungen/zeitplan.mjs) prueft ihren Startablauf.

## Figuren, Herkunft und Promptdateien

Originale Referenzen unveraendert in [figuren/](figuren/): Business mit
Hut, grauem Anzug und Taschenuhr; AI mit schwarzer Lederjacke und cyan Brille.
Eigene GTA-artige gemalte Spielwelt, keine kopierten Spielfiguren oder Szenen.
Die bisherigen Videos verwenden Standillustrationen mit Kamera-/Schnittbewegung,
keine vollstaendige Koerperanimation.

Exakte Bildauftraege und Referenzen:

- [PROMPTS.json](assets/illustrationen/PROMPTS.json): erste vier Bilder.
- [ERWEITERUNG-PROMPTS.json](assets/illustrationen/ERWEITERUNG-PROMPTS.json): zehn weitere Motive.
- [BUSINESS-FIGUR-PROMPTS.json](assets/illustrationen/BUSINESS-FIGUR-PROMPTS.json): zwei Business-Handlungsszenen.

Alle projektverwendeten Bilder liegen im Repository, nicht nur im Codex-
Generierungsordner. Cloudflare meldete am 05.10.2026 ein erschoepftes freies
Tageskontingent. Die neue Bibliothek ermoeglichte beide Videos ohne weitere
Cloudflare-Bildgenerierung; keine kostenpflichtige Hochstufung aktiviert.

## Erneut ausgefuehrte Tests

Am 05.10.2026 fuer diese Uebergabe erneut lokal ausgefuehrt, alle erfolgreich:

| Pruefung | Ergebnis | Nachweis |
|---|---|---|
| Python-Regressionssuite | 154 Tests, bestanden, Exitcode 0 | [regression.txt](pruefungen/ergebnisse/2026-10-05/regression.txt) |
| Python-Syntaxpruefung | `compileall`, Exitcode 0 | [compileall.txt](pruefungen/ergebnisse/2026-10-05/compileall.txt) |
| Zeitplan-/Worker-Pruefungen | 5 Pruefungen bestanden, Exitcode 0 | [zeitplan.txt](pruefungen/ergebnisse/2026-10-05/zeitplan.txt) |

[ergebnis.json](pruefungen/ergebnisse/2026-10-05/ergebnis.json) speichert
Ausfuehrungszeit, Python-Version, genaue Befehle und Exitcodes. Die Syntax-
pruefung ist absichtlich still; ihr erfolgreicher Exitcode steht im Bericht.
Regressionen verwenden Testdoubles: absichtliche Fehlermeldungen und simulierte
Telegram-Ausgaben im Testlog sind keine echten Produktionsereignisse.

Vom Projektstamm reproduzierbar:

```text
python -m unittest discover -s pruefungen -v
python -m compileall -q fabrik pruefungen
node pruefungen/zeitplan.mjs
```

Lokal benoetigt die Suite Python mit `pillow` und `numpy` sowie Node.js.
Die vorhandene [CI-Konfiguration](.github/workflows/pruefen.yml) nutzt Python
3.12 / Node 22. Bereits erfolgreiche CI-Nachweise fuer die Bibliotheksumsetzung:
[37353556999](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37353556999)
und [37353765649](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37353765649).

Die zentralen Regressionen pruefen insbesondere:

| Testdatei | Wesentlicher Schutz |
|---|---|
| [test_bibliothek.py](pruefungen/test_bibliothek.py) | Alle 16 Originaldateien und Hashes; fremder Kanal/Pfadausbruch/veraenderte Datei abgewiesen; komplette AI-Regie fuer die gemessene Stimme ohne Bildgenerierungsauftrag; vier eindeutige Demos; zu kurze Regie stoppt. |
| [test_bildplan.py](pruefungen/test_bildplan.py) | Mehrere Einstellungen je Sprechphase, Ton erhalten; Zooms zaehlen nicht neu; kumulierte Motivhaltezeit; Luecken/leere Hintergruende/fehlender Schluss; Nutzerablehnung verhindert Versand trotz KI 9. |
| [test_quellen.py](pruefungen/test_quellen.py) | Primaerquellen, Beispielbilder und Quellenbezug; begrenzte Anreicherung; Bilddateien und Auswahl. |
| [test_prompts_ton.py](pruefungen/test_prompts_ton.py) | Promptregeln, Figurenpruefung/-referenz, Bildgenerierungsanfrage sowie TTS-/Musik-/Effektgrenzen. |
| [test_pilot_entwurf.py](pruefungen/test_pilot_entwurf.py) | Kein Uebernehmen alter Freigaben; erneute Fakten-/Storypruefung; falscher Kanal und unzureichende Story stoppen. |
| [test_korrektur.py](pruefungen/test_korrektur.py) | Korrektur-/Cacheverhalten, unveraenderter Ton und unbetroffene Clips; keine Lernstandards aus erfolglosen/ungeprueften Versuchen. |
| [test_telegram_feedback.py](pruefungen/test_telegram_feedback.py), [test_statusmeldung.py](pruefungen/test_statusmeldung.py) | Feedback statt falscher Themenqueue; Deduplizierung und Statusmeldungen. |
| [test_github_transfer.py](pruefungen/test_github_transfer.py) | Sichere Artefaktpfade und Redirects bei GitHub-Downloads. |
| [test_betrieb.py](pruefungen/test_betrieb.py), [test_dramaturgie.py](pruefungen/test_dramaturgie.py) | Produktions-/Freigabefilter, Versand, Budget, Dramaturgie, Formate und Zeitverhalten. |

## Echte Videopruefung und Zustellbelege

Die folgenden Nachweise stammen aus Produktionslaeufen, nicht aus Unit-Testdoubles:

| Nachweis | AI Tools Explained | Business Origin Stories |
|---|---|---|
| Produktionslauf | 37353822179 | 37354061119 |
| Story / Video laut KI | 8 / 8 | 8 / 8 |
| Fakten-/Technikbefunde | Keine offenen Befunde | Keine offenen Befunde |
| MP4 | 1080x1920, H.264, 30 fps | 1080x1920, H.264, 30 fps |
| Ton | AAC Stereo 48 kHz, -14,9 LUFS | AAC Stereo 48 kHz, -14,1 LUFS |
| Versandlauf | 37355648862 | 37356701658 |
| Telegram-Video bestaetigt | message_id 123, 20:24:57 Berlin | message_id 130, 20:33:15 Berlin |
| Empfang durch Nutzer | Ausdruecklich bestaetigt | Ausdruecklich bestaetigt |

MP4, `kritik.json`, `messung.json`, `bildablauf.json` und Skript lokal unter
`ausgabe/github/11363059750/ausgabe/` (AI) und
`ausgabe/github/11364637569/ausgabe/` (Business). Kontaktboegen unter
`ausgabe/videoanalyse/ai-neu-kontaktbogen.jpg` und
`ausgabe/videoanalyse/business-neu-kontaktbogen.jpg`.
Zustellbelege/Hashes/qualitatives Nutzerfeedback dauerhaft in
[telegram-sendungen.json](verlauf/telegram-sendungen.json).

## Naechste konkrete Arbeiten

AI: fuer vergleichbare Shorts 14-18 sinnvolle Motive vorbereiten. Business:
bei etwa 24 Einstellungen auf 18 Motive zielen, also vier Wiederholungen durch
neue passende Motive ersetzen. Dafuer die jeweilige Bibliothek/Regie sinnvoll
erweitern, neue Bilder sichten, Kanal/Motiv/Hash katalogisieren und die echte
Bildfolge pruefen. Die bisherigen Pilotvorlagen und MP4s sind noch 23/12 bzw.
24/14; diese Uebergabe erzeugt keine neue 18-Motive-MP4.

Die Ziele sind bereits in den wirksamen Redaktionsregeln hinterlegt. Der native
Vielfaltsfilter ist weiterhin laengenabhaengig, kein neuer harter 18-Motive-
Versandfilter. Bei fest vorgegebener Pilotregie muss Claude auch die konkrete
Bildfolge erweitern; Lernregeln allein aendern eine solche feste Vorlage nicht.

Vor Versand fertige MP4 kontrollieren, Fakten und Technik pruefen und die
reale Telegram-Zustellung bestaetigen. Die automatische Gesamtpruefung und
Unit-Tests garantieren keine 10/10 oder Zuschauerbindung; das Nutzerurteil
bleibt entscheidend. Die 10/10-Zielsetzung darf keine Noten kuenstlich erhoehen.
