# Contentfabrik

Stand: 06.10.2026. Eine private Cloud-Pipeline fuer eigene englische
Kurzvideos: **AI Tools Explained** und **Business Origin Stories**.
Ziel sind gute Originalinhalte mit moeglichst 0 EUR laufenden Kosten.

## Was heute funktioniert

1. Themen aus oeffentlichen Quellen oder der Telegram-Warteschlange.
2. Skript, Quellen-/Faktencheck, Zahlenprobe und Story-Bewertung.
3. Kokoro-Stimme, ffmpeg-Video, Untertitel, Bilder/Clips und Soundeffekte.
4. Technische Messung, unabhaengige Kontrolle des gesprochenen Like/share/save
   im fertigen MP4-Ton, danach KI-Bewertung des fertigen Videos.
5. Ab **7/10 fuer Skript und Video**, jeder Einzelkategorie mindestens 7/10
   (nur die Story-Teilbarkeit darf als unsichere Prognose 6/10 haben),
   ohne offene mittlere/schwere Probleme, mit bestandenen Fakten, Technik und Endton:
   Video-Vorschau und Upload-Texte an den Betreiber in Telegram.
6. Lernen aus den Pruefungen; YouTube-Auswertung mit eingerichteten Zugaengen.

Neu: befristete Gemini-Sperren und Wiederverwendung identischer KI-Pruefungen
mit sechs Stunden Gueltigkeit. Beschreibung, echte CTA-Tonproben und Tests:
[KONTINGENT-UND-ENDTON.md](KONTINGENT-UND-ENDTON.md).

**Der aktive Tageslauf veroeffentlicht nichts selbst.** Der Betreiber prueft
die Telegram-Vorschau und laedt das Video in der Plattform-App hoch.
`gesendet` im Verlauf bedeutet Telegram-Zustellung, keine Veroeffentlichung.
Ein Dashboard, Freigabe-Knoepfe und geplante automatische Uploads sind noch
nicht Teil dieses Ablaufs. Die Website ist die Informationsseite fuer die
Plattform-Antraege.

## Verbesserungen vom 05.10.2026

Neu am 06.10.2026: [kostenlose Werkzeuge fuer die gesamte Pipeline](KOSTENLOSE-PIPELINE.md)
mit belegten API-/Hardwaregrenzen. Ein [kontrollierter Autorenvergleich](vergleiche/autoren/README.md)
testet Gemini gegen GPT-OSS anhand gleicher Quellen; Standardautor und
Tagesproduktion werden dadurch nicht ungeprueft umgestellt.

Neu am 06.10.2026: [Qualitaetsserie im normalen Automatiklauf](QUALITAET-AUTOMATIK.md)
mit zunaechst drei Shorts je Kanal, getrennten KI-/Sichtpruefungen und dauerhaftem
Protokoll in `verlauf/qualitaetsserie.json`. Zehn menschlich bestaetigte Erfolge
in Folge je Kanal sind ein Kontrollpunkt; Plattform-Uploads bleiben manuell.

- Fehlende/ausgefallene Video-Pruefung ist keine kuenstliche 8/10 mehr.
  Auch ein direkter Aufruf von `freigabe.py` kann diese Sperre nicht umgehen.
- Technikfehler sperren das Video vollstaendig; sie senken nicht nur die Note.
  Defekte Videos verbrauchen keine KI-Anfrage fuer die Video-Bewertung.
- Alle Tagesfenster teilen **30 Minuten je Kanal und UTC-Tag**, gespeichert
  in `verlauf/budget/<kanal>.json`. Unterprozesse haben eine gemeinsame
  Deadline; das Lernen bekommt davon hoechstens 90 Sekunden.
- Vor Arbeitsbeginn wird das Restbudget reserviert, beim normalen Ende die
  ungenutzte Zeit erstattet. Bei einem harten Prozessabbruch bleibt die
  Reservierung erhalten, sofern der Sicherungsschritt noch ausgefuehrt wird.
- Video- und Themen-Workflows schreiben nacheinander. Beide Kanaele lesen
  den aktuellen Stand von `main`; neue Kanaele werden aus `kanaele/*.json`
  erkannt. Fehler beim Sichern lassen den Workflow sichtbar fehlschlagen.
- Manuelle Themen werden als Daten an Python uebergeben und bei einem
  erneuten Versuch beibehalten.
- Telegram-Texte werden vollstaendig aufgeteilt. Lizenzangaben werden nicht
  abgeschnitten; `ok=false` gilt als Zustellfehler.
- Der Cloudflare-Zeitplan meldet abgelehnte GitHub-Starts als Fehler.

Das Tagesbudget begrenzt die Produktion, **nicht** die gesamte GitHub-Rechnung:
Einrichtung, Caches, Themen-Abholung, Tests und Sicherung brauchen ebenfalls
Minuten und Speicher. Bei 31 Tagen sind allein 2 × 30 Minuten × 31 = 1.860
Produktionsminuten moeglich. Verbleibende Freikontingente im Konto pruefen;
die bisherigen Pilotzeiten sind keine Kapazitaetsgarantie fuer heutige Videos.
Ein vollstaendig abgebrochener Workflow ohne Sicherung kann auch den
Budgetstand verlieren. Parallele lokale Produktionslaeufe sind nicht vorgesehen.

## Lokal pruefen

Python 3.12+, Pillow, NumPy und Node.js 22+ fuer die Tests; keine API-Schluessel
oder Videomodelle erforderlich. Die Tests senden keine Nachrichten; externe
KI-Anfragen und ffmpeg werden fuer die Ablaufpruefungen ersetzt.

```powershell
pip install pillow numpy
python -m unittest discover -s pruefungen -v
python -m compileall -q fabrik pruefungen
node pruefungen/zeitplan.mjs
```

Der Workflow `pruefen.yml` fuehrt diese Kontrollen auch bei Codeaenderungen
aus. Die Produktionsabhaengigkeiten stehen in `requirements.txt`; zum Bauen
braucht es ausserdem ffmpeg/ffprobe, Kokoro-Modelle und die passenden
Umgebungsvariablen aus `video.yml`. Zugaenge gehoeren in GitHub Secrets.

Ein einzelner Produktionslauf verwendet dieselben Pruefungen und dasselbe
Tagesbudget wie der Cloud-Ablauf:

```powershell
python fabrik/lauf.py kanaele/business-origin-stories.json
```

Dieser Befehl erzeugt echte API-Anfragen und schickt bei Erfolg eine
Telegram-Vorschau. Fuer die Kontrolle des Codes genuegen die Tests oben.

## Gezielte Nachbesserung und Lernen (05.10.2026)

Die ueberarbeiteten Auftraege je KI sowie die Verbesserungen an Bildauswahl,
Stimme, Musik und Effekten sind in [PROMPTS.md](PROMPTS.md) dokumentiert.
Gemeinsame Vorlagen stehen in `fabrik/prompts.py`; Skript und Video-Kritik
speichern die Vorlagenversion fuer spaetere Vergleiche.

Der Tageslauf erstellt zunaechst ein Video und arbeitet dann am selben
Entwurf weiter. Hoechstens zwei Korrekturrunden innerhalb des Tagesbudgets:

1. Aus konkreten Pruefproblemen und Kategorien die schwaechste umsetzbare
   Eingriffsart waehlen (Bild, Untertitel, Ton, Stimme, Tempo oder Story).
2. Zeitstempel bzw. Zeitbereiche den gemessenen Abschnitten zuordnen.
   Bildkorrekturen duerfen nur diese Abschnitte aendern; fehlende Zeitmarken
   sind kein Anlass, beliebige Bilder auszutauschen.
3. Unveraenderte Stimme/Zeitmarken und fertige Videoteile wiederverwenden.
   Fingerabdruecke pruefen Text, Stimme, Tempo, Titel, Bilder und Baucode.
   Das abschliessende Zusammenbauen und die fertige Video-Pruefung laufen
   erneut. Bei geaendertem Sprechtext: erneuter Quellencheck, Zahlenprobe,
   optionaler Zweitpruefer und Story-Bewertung vor dem Bau.
4. Ergebnis davor/danach und Laufzeit in `lernen/<kanal>.json` speichern.
   Schlechtere Fassungen ersetzen kein bereits bestandenes Video. Ausfaelle
   ohne neue Note bleiben protokolliert und werden nicht als Wirkungsnachweis
   fuer eine Einstellung verwendet.

Eine Eingriffsart pro Runde erleichtert die Zuordnung der Wirkung. Gemischte
Eingriffe beeinflussen die automatische Profilwahl nicht. Mit wenigen Daten
werden weniger getestete Varianten gewaehlt; ab drei Messungen bevorzugt
die Wahl erfolgreichere Varianten. Untertitel-/Tonprofile werden auch fuer
neue Videos uebernommen, wenn mindestens drei einzelne Korrekturen vorliegen
und mehr als 60 % davon Verbesserungen ergaben. Das sind vorlaeufige
Erfahrungswerte, kein Beweis fuer mehr Aufrufe. Stimme und Themenwinkel
lernen weiterhin ueber `erfolg.py` aus echten YouTube-Zahlen.

`ausgabe/bericht.json` dokumentiert jede Runde mit Note, Problemen, Zeiten
und wiederverwendeten/neuen Abschnitten. Die letzten 60 Betriebsberichte
stehen in `verlauf/messungen/<kanal>.json`. GitHub zeigt eine lesbare
Zusammenfassung des aktuellen Laufs. Der bestehende Regelspeicher bleibt
beim Lernen und beim Abruf der Zuschauerzahlen erhalten.

Alte Skripte ohne gespeicherte Quelltexte bekommen Bild-/Darstellungskorrekturen;
ihr Sprechtext wird nicht mit einer alten Freigabe neu geschrieben. Die
Untertitelprofile veraendern Darstellung/Gruppierung, keine behauptete
automatische Reparatur beliebiger Synchronisationsfehler. Nicht umsetzbare
Kritik wird dokumentiert; eine hoehere Note wird nicht garantiert.

## Zuschauerbindung fuer Shorts und lange Videos

`fabrik/dramaturgie.py` gibt Autor und beiden Redaktionen dieselben Formatregeln:
eine konkrete Leitfrage, neue Information je Abschnitt, kleine Antworten
unterwegs und eine vollstaendige Aufloesung. Shorts beginnen direkt beim
Thema. Lange Videos bekommen Kapitel mit eigenen Fragen, Belegen und
Zwischenantworten. Spannung entsteht aus belegten Entscheidungen und
Konsequenzen; erfundene Krisen oder wiederholte Ankuendigungen sind keine
Loesung fuer duenne Quellen.

Der Autor plant Fotos, Originalkarten, Clips und Illustrationen nach Inhalt.
Optionale `bildtext`-Akzente zitieren 2-5 zusammenhaengende Woerter aus dem
Sprechtext. Sie erscheinen an deren Wortzeiten, hoechstens in jedem zweiten
Abschnitt; falsche Phrasen und unpassende Zeiten bleiben unsichtbar.
`dramaturgie.json` dokumentiert die gemessenen Beats und Einblendungen.
Fotos und Karten passen zwischen Titel und Untertitel, Untertitelgruppen
werden nach Pixelbreite begrenzt und enden vor langen Sprechpausen.
Echte Clips und Demos bekommen keine periodischen Zoomspruenge mehr.
Langvideos vertonen Kapitelwechsel und markierte Wendungen gezielt; ein
normaler Abschnittswechsel bekommt dort keinen automatischen Whoosh.

Der Renderer und die technische/inhaltliche Pruefung unterstuetzen jetzt
auch `videoformat: "lang"` mit 1920 x 1080, eigener Laenge und ruhigeren
Untertiteln.
Die gemessene Sprechdauer kann eine zweite Synthese mit begrenzt angepasstem
Tempo ausloesen; lange Videos bleiben zwischen 0,90 und 1,15. Eine danach
unpassende Dauer besteht die technische Pruefung weiterhin nicht.
Ein optionales Profil liegt ausserhalb der taeglichen
Shorts-Auswahl in `formate/business-origin-stories.json`. Lokaler Pilot mit
installierten Produktionsabhaengigkeiten und vorhandenen Zugaengen:

```powershell
$env:CF_PILOT = "1"
python fabrik/lauf.py formate/business-origin-stories.json "Nintendo"
Remove-Item Env:\CF_PILOT
```

Das Beispiel plant 6-8 Minuten, braucht eine ausfuehrliche Quelle und teilt
weiterhin das begrenzte Pilot-Tagesbudget desselben Kanals. Der bestehende
Cloud-Zeitplan bleibt bei Shorts. Der separate Doku-Skripteditor
`fabrik/doku.py` nutzt ebenfalls Langformat-Regeln und sperrt schwache
Skripte; seine Kapiteldatei ist kein direktes Renderer-Eingabeformat.
Ein echter Langvideo-Render ist noch nicht durchgefuehrt; insbesondere
Renderzeit und Wirkung muessen im Pilot geprueft werden.

YouTube-Zahlen vergleichen Shorts und Langvideos getrennt. Kurven werden
erst bei oeffentlichen Videos ab 48 Stunden und 100 Aufrufen ausgewertet,
bei mindestens 50 % Wachstum oder nach sieben Tagen erneut abgerufen.
Ein lokaler Verlust braucht zwei bestaetigende Messpunkte; einzelne
Ausreisser, normale langsame Abnahme und der letzte Videoabschnitt werden
nicht vorschnell zu allgemeinen Regeln. 100 Aufrufe und die Schwelle von
0,10 sind vorsichtige interne Heuristiken, kein statistischer Wirksamkeitsbeweis.
Ein Kurvenknick kann Ueberspringen oder Ausstieg bedeuten; er zeigt allein
keine Ursache. Referenzen: [YouTube Zuschauerbindung](https://support.google.com/youtube/answer/9314415),
[offizielle Analytics-Metriken](https://developers.google.com/youtube/analytics/metrics).

Die Freigabe liegt auf ausdruecklichen Nutzerwunsch bei 7/10: ein guter Durchschnitt verdeckt
keine schwache Story, unlesbaren Text oder schlechte Stimme. Dadurch kann
ein Tag ohne geeignetes Video enden. Die Note ist ein unabhaengiges redaktionelles
Urteil, keine Zusage, dass alle Zuschauer bis zum Ende bleiben.

## Echter Cloud-Probelauf

Der manuell startbare Workflow `.github/workflows/pilot.yml` baut mit den
echten Modellen und bewertet das Video mit Gemini. Mit `telegram=true` sendet
er ausschliesslich bestandene Videos samt Skript und Upload-Texten auf Telegram.
Er bestaetigt dann auch den Start und meldet abgelehnte/abgebrochene Laeufe
mit ihrem Grund. Ein eigener Fehlerjob meldet Fehlschlaege des Hauptjobs;
bereits bestaetigt zugestellte Videos werden nicht als fehlend gemeldet.
Ohne diese Auswahl bleiben die Ergebnisse privat auf GitHub. Er laedt nichts auf Plattformen hoch und schreibt nichts
nach `main`. Ergebnisse und Lernprotokolle liegen drei Tage als private
Artefakte vor. Start erst mit dem neuen Code auf GitHub und vorhandenem
`GEMINI_API_KEY` in den Repository-Secrets. Weitere Bild-/Clip-Zugaenge
werden aus den vorhandenen Secrets genutzt.
Die Auswahl `videoformat=lang` verwendet das optionale Business-Profil;
nicht vorhandene Format-/Kanal-Kombinationen brechen vor der Einrichtung ab.
Der Pilot hat ein eigenes, auf 30 Minuten begrenztes Budget pro Kanal und
meldet einen gesperrten Entwurf als fehlgeschlagene Qualitaetspruefung.

Der gespeicherte GitHub-Zugang ist ueber den Windows Credential Manager
verfuegbar; der Zugriff auf dessen geschuetzten Speicher braucht hier eine
Sandbox-Freigabe. Produktionsschluessel bleiben in GitHub-Secrets.
Lokal gibt es kein ffmpeg/ffprobe; die echten Videos entstehen im Cloud-Pilot.
Telegram bekommt bei zu grossen Dateien eine komprimierte Vorschau und den
Verweis zum privaten GitHub-Artefakt mit dem Original in voller Qualitaet.
Bei Langvideos entfallen `#shorts` und der TikTok-Uploadtext.

Die ersten beiden Nintendo-Piloten scheiterten VOR dem Render: Short am
Faktencheck, Langvideo mit Story 6/10 (dessen Themenwahl wechselte zu Apple).
Sie belegen noch keine Videoverbesserung. Details und die Korrektur der
fehlenden Telegram-Statusmeldungen stehen in `UEBERGABE-CLAUDE.md`.
Der anschliessende [Nintendo-Short-Pilot](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37331710289)
hat dagegen ein echtes 89,7-Sekunden-Video geliefert: Skript 8/10,
Video 8 → 9/10 nach gezielter Bildkorrektur, Telegram-Versand erfolgreich.
**Vom Nutzer anschliessend als <5/10 abgelehnt:** zu wenige Bilder und
lange Kerzenhintergruende. Die KI-9 bestaetigt keine professionelle Qualitaet.
Neu sind mehrere Gemini-geplante Einstellungen pro Sprechphase, echte
Bildabdeckungspruefung und dauerhaftes menschliches Feedback fuer beide Kanaele.
Mindestnote ist auf Nutzerwunsch 7/10; die Notenskala bleibt unveraendert.
Die lokale Kontrolle prueft Ablauf, Quellen-Sperren, Cache und Lerngedaechtnis
mit Ersatzantworten; sie belegt noch keine Verbesserung eines echten Videos.

## Weitere Schritte

1. Den vorbereiteten Cloud-Pilot ausfuehren und messen: Anteil bestandener Videos, Minuten pro
   freigabefaehigem Video, Gruende fuer Sperren und Telegram-Zustellung.
2. Kanal-Dashboard mit Status, Budget, Vorschau und ausdruecklicher Freigabe.
   Vor automatischer Veroeffentlichung muss die Freigabe gespeichert werden;
   blosses Nicht-Verwerfen ist keine Freigabe.
3. Nach geklaertem YouTube-Audit Uploads mit stabiler Video-ID, gespeicherter
   Freigabe und Schutz vor doppelter Veroeffentlichung anbinden.

## Dokumente und offene Plattform-Fragen

| Datei | Zweck |
|---|---|
| [UEBERGABE-CLAUDE.md](UEBERGABE-CLAUDE.md) | Neue Aenderungen, getesteter Stand, echte Laeufe und Fortsetzung fuer Claude |
| [CLAUDE.md](CLAUDE.md) | Kurzer Einstieg und Verweis auf die Uebergabe |
| [KONZEPT.md](KONZEPT.md) | Gesamtziel, Ideen, historische Messungen; aktuelle Einordnung am Anfang |
| [ANLEITUNG-YOUTUBE.md](ANLEITUNG-YOUTUBE.md) | Einmalige Einrichtung, mit Hinweis zum heutigen Umfang |
| [GOOGLE-ANTRAG.md](GOOGLE-ANTRAG.md) | Eingereichter Antrag vom 04.10.; beschreibt auch geplante Funktionen |
| [TIKTOK-ANTRAG.md](TIKTOK-ANTRAG.md) | Entwurf und konkretes Hindernis fuer Direct Post |
| [sfx/LIZENZ.md](sfx/LIZENZ.md) | Herkunft/Lizenzen der Soundeffekte |
| `website/` / `antrag/` | Informationsseiten und Antragsnachweise |

TikTok nennt reine Werkzeuge zum Hochladen auf eigene/Team-Konten als
unzulässigen Anwendungsfall fuer Direct Post. Deshalb ist die Pruefung des
privaten Tools kein zugesicherter Weg zum oeffentlichen Auto-Upload. Quelle:
[TikTok, Intended Use](https://developers.tiktok.com/docs/en/content-sharing-guidelines),
abgerufen 05.10.2026. Bis zur Klaerung bleibt der aktive Ablauf beim manuellen Upload.

Die 2027-YPP-Schwellen sind inzwischen auf der offiziellen Seite bestaetigt:
ab 01.02.2027 fuer neue Werbe-/Premium-Teilnehmer 1.000 Abos und 8.000
qualifizierte Stunden oder 20 Mio. qualifizierte Shorts-Aufrufe. Quelle:
[YouTube, Aenderungen am Partnerprogramm](https://support.google.com/youtube/answer/12843009),
abgerufen 05.10.2026. Die Schwellen allein garantieren keine Aufnahme.

YouTube dokumentiert getrennte Tageskontingente fuer `search.list` und
`videos.insert` (je 100 Aufrufe) sowie 10.000 Einheiten fuer andere Methoden.
Die frueher eingereichte Rechnung mit 1.600 Einheiten je Upload bleibt als
Historie im Antrag; fuer den Betrieb gelten die Werte der Cloud Console.
Quelle: [YouTube, Kontingente](https://developers.google.com/youtube/v3/determine_quota_cost),
abgerufen 05.10.2026. Die Zusammenfassung dieser Seite enthaelt noch alte
Zahlen; Haupttext und Methodentabelle nennen die getrennten Kontingente.

Workflow-Warteschlangen verwenden `queue: max` mit einer gemeinsamen
Concurrency-Gruppe. Quelle:
[GitHub, Workflow-Concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
abgerufen 05.10.2026.
