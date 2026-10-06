# Kontingent sparen und gesprochenen CTA pruefen

Stand 06.10.2026. Diese Erweiterungen funktionieren unabhaengig vom noch
offenen Autorenvergleich. Sie erzeugen selbst keine neuen Videos. Der
Standardautor bleibt Gemini; keine neue kostenpflichtige Stufe und keine
Kontenrotation. Heute ist noch kein neuer erfolgreicher Tagesfilm bestaetigt.

## Befristete Fehlerbehandlung

`fabrik/ki_speicher.py` und `skript.gemini()` speichern erkannte Sperren in
`verlauf/gemini-kontingent.json`. Die normale Verlaufssicherung nimmt diese
Datei mit. Ein erkannter HTTP-429-Tagesfehler sperrt das betroffene Modell
bis zur naechsten Mitternacht in America/Los_Angeles; Sommer-/Winterzeit wird
beruecksichtigt. Windows braucht dafuer `tzdata`, jetzt in requirements.txt.
Fehlen Zeitzonendaten, gilt konservativ eine 24-Stunden-Sperre.

404: 24 Stunden, 503: fuenf Minuten. Beim Minuten-/Tokenlimit maximal eine
Wiederholung mit Retry-After, hoechstens 60 Sekunden warten. Laengere
Retry-After-Fristen werden gespeichert statt im Prozess abgewartet. 400,
401 und 403 werden ohne blinde Wiederholungen als Anfragefehler gemeldet.
Sperren laufen aus; ein temporaerer Ausfall sperrt ein Modell nicht dauerhaft.
Kein Geheimnis oder API-Fehlertext wird gespeichert; Zugang nur ueber einen
Hash zugeordnet. Diese lokale Zuordnung ist kein Projekt-Quota-Zaehler:
zwei Schluessel desselben Google-Projekts teilen weiterhin dessen Limits.
Aliase sind kein Nachweis unabhaengiger Kontingente.

## Wiederverwendung identischer KI-Pruefungen

Expliziter Cache fuer Fakten-/Storypruefungen in `skript.py` und den
erneuten Faktencheck in `nachbessern.py`, zusaetzlich fuer fertige
Videokritiken in `kritik.py`. Gueltigkeit sechs Stunden. Der Cache-Schluessel
enthaelt exakten Prompt mit Quelltext/Skript, Schema, Modellreihenfolge,
Temperatur und Zweck; bei Video zusaetzlich SHA256 der gesamten MP4.
Geaenderte Quellen, Sprechtexte, Pruefkriterien oder Videobytes verlangen
eine neue Pruefung. JSON wird vor Speicherung und Wiederverwendung
rekursiv gegen das erforderliche Schema geprueft. Abgeschnittene,
fehlgeschlagene oder unvollstaendige Antworten werden nicht gespeichert.
Auch ein gueltiges negatives Urteil bleibt negativ; ein Cache-Treffer
ist keine neue KI-Anfrage und wird entsprechend protokolliert.

Der lokale Ordner `ki-cache/` ist git-ignoriert. Video-/Pilot-Workflows
stellen ihn ueber GitHub Actions Cache wieder her und sichern ihn auch bei
einem spaeteren Produktionsfehler. TTL wird immer im Code kontrolliert;
ein vorhandener Actions-Cache allein reicht nicht. Kein kreativer
Skriptentwurf und keine Anfrage des Autorenvergleichs verwendet diesen
Pruefcache. Technik, Bildablauf und Audio-Pruefung laufen auch bei einem
Videokritik-Cache-Treffer erneut. Sind alle bekannten Modelle gesperrt
und liegt keine identische Kritik vor, entfaellt der unnoetige Video-Upload.
Tatsaechlich gesparte Tages-Tokens sind noch nicht im echten Tageslauf gemessen.

## Unabhaengiger Check des fertigen Tons

`fabrik/sprachpruefung.py` transkribiert die fertige MP4 mit Whisper base.en,
CPU INT8, VAD und Wortzeitstempeln. Es gibt keinen Skriptprompt, keine
Hotwords, keine Uebernahme der angeglichenen Untertitel und keine
Fortschreibung vorheriger Segmente. Alle drei Aktionen muessen im selben
kurzen englischen Aufruf erkannt werden: `like, share and save this video`.
Wortwahrscheinlichkeiten begrenzen unsichere Treffer; verstreute Verben
oder nur Subscribe/Like/Share reichen nicht.

Short: innerhalb der letzten 20 Sekunden (bei laengeren Shorts maximal
60 Sekunden bzw. 15 Prozent). Langvideo: zuerst ab Sekunde 3 bis zur
kleineren Grenze aus 90 Sekunden und dem ersten Viertel; ausserdem am Ende
im entsprechenden Schlussfenster. Diese Fenster sind technische
Platzierungspruefungen. Ob der erste Aufruf erst nach dem ersten Nutzwert
kommt und die Aufloesung gelungen ist, pruefen Redaktion und Mensch.

`audio-pruefung.json` enthaelt unveraenderte erkannte Woerter, Zeiten,
Wahrscheinlichkeiten, Einstellungen, Bibliotheksversion und Video-SHA256.
Identisches MP4 und identische ASR-Einstellungen duerfen das Rohtranskript
wiederverwenden; Format/Dauer/CTA-Fenster werden erneut geprueft. Ein
Erkennungsfehler oder fehlender Aufruf sperrt den Versand und spart die
anschliessende Gemini-Videopruefung. `qualitaet.py` prueft die Rohdaten
erneut, statt nur `ok=true` zu vertrauen. `freigabe.py` verlangt die zur
konkreten Datei passende SHA256. Alte Kritiken ohne Endton-Nachweis sind
fuer kuenftigen Versand nicht mehr ausreichend; bereits gelieferte Piloten
bleiben historische Ergebnisse und werden nicht erneut gesendet.

ASR kann falsch erkennen oder einen vorhandenen Aufruf ueberhoeren. Die
volle menschliche Sicht-/Hoerpruefung bleibt erforderlich; dies ist keine
Garantie fuer Verstaendlichkeit, Gesamtqualitaet, Fakten oder Zuschauerbindung.
Andere englische CTA-Formulierungen brauchen gegebenenfalls eine Erweiterung
des Erkenners. Die produktiven Prompts verwenden die gepruefte Formulierung.

## Echte Tonproben und Tests

Die Dateien stimmen per SHA256 mit den am 05.10. bereits auf Telegram
gelieferten Piloten ueberein:

| Probe | Unabhaengiger ASR-Befund |
|---|---|
| AI Tools Explained, Qwen Image, 82,2 s | Like/share/save bei 79,78-81,64 s erkannt |
| Business Origin Stories, Nintendo, 89,7 s | Like/share/save bei 87,08-89,20 s erkannt |
| Kontrollkopie des AI-Videos nach 75 s abgeschnitten | Kein CTA erkannt, gesperrt |

Nachweise und vollstaendige Rohtranskripte:
`pruefungen/ergebnisse/2026-10-06/endton-piloten.json` sowie die dort
verlinkten `endton-*.json`. Keine Gemini-/Groq-Anfrage oder Telegram-Nachricht
fuer diese Proben. Kein neues Tagesvideo, keine neue Nutzerbewertung. Eine
echte Langvideo-Tonprobe fehlt; beide Zeitfenster mit kuenstlichen Rohdaten getestet.

Beim ersten realen Test: schneller ASR-Abbruch durch `metadata_errors`
mit faster-whisper 1.2.1 / PyAV 19.0.1. Die Upstream-Korrektur steht bereits
im Entwicklungszweig, aber nicht in der installierten Version. Darum
`faster-whisper==1.2.1` und `av>=11,<19` festgelegt. Obige erfolgreichen
Proben liefen mit PyAV **18.1.0** auf Windows/Python 3.13. Abhaengigkeiten
lokal unter dem ignorierten `modelle/python-audiopruefung/` installiert.

**208 Regressionstests bestanden**, davon 28 neue Kontingent-/Cache-/Tonchecks,
5,955 s im dokumentierten lokalen Lauf; Kompilierung und fuenf Node-
Zeitplanpruefungen bestanden. Tests pruefen u. a. Reset in Sommer/Winter,
befristete Sperren, Fehler ohne Schluesselleck, frische kreative Anfragen,
Cache-Invalidierung, abgeschnittene Antworten, CTA-Sperren, Bindung an die
Videodatei und Auslassen unnoetiger Uploads. Unit-Tests verwenden Testdaten,
die drei echten Tonproben sind getrennt dokumentiert.

GitHub-CI [37448448528](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37448448528)
am Code-Commit `5530ba6` erfolgreich: 208 Tests in 1,497 s, Kompilierung
und Node-Pruefungen bestanden. Ein CI-Erfolg ist kein neuer Videoerfolg.

Reproduktion im Workspace mit installierten requirements:

```powershell
python -m unittest discover -s pruefungen -v
python -m compileall -q fabrik pruefungen
node pruefungen/zeitplan.mjs
python fabrik/sprachpruefung.py ausgabe/github/11363059750/ausgabe/short.mp4 ausgabe/github/11363059750/ausgabe/skript.json 82.2
python fabrik/sprachpruefung.py ausgabe/github/11364637569/ausgabe/short.mp4 ausgabe/github/11364637569/ausgabe/skript.json 89.7
```

Tests unter `pruefungen/test_ki_speicher.py` und
`pruefungen/test_sprachpruefung.py`; Protokolle unter
`pruefungen/ergebnisse/2026-10-06/kontingent-endton-*`.

Primaerquellen: [Gemini-Limits](https://ai.google.dev/gemini-api/docs/rate-limits),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[PyAV-19-Kompatibilitaet im Upstream-Code](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/audio.py).
