# Autorenvergleich, 06.10.2026

Beauftragt: Gemini und Groq GPT-OSS-120B anhand derselben Quellen vergleichen,
bevor ein anderer Standardautor in den Tageslauf uebernommen wird.

Sechs eingefrorene Quellenpakete in `faelle.json`: Qwen Image, Kokoro, Whisper
sowie Nintendo, LEGO und Nike. Die ersten beiden stammen aus gespeicherten
Pilot-Quellen, ohne die Pilot-Narration zu uebernehmen. Vier Quellen wurden
am 06.10. frisch abgerufen. Quelle, Herkunft und Text-Hash sind gespeichert.

Ausfuehrung: Workflow `autorenvergleich.yml`, Eingabe `anzahl=3`. Der gemeinsame
Auftrag verlangt 190-220 englische Woerter, 8-10 Sprechphasen, einen konkreten
Einstieg und dessen Aufloesung sowie genau einen gesprochenen like/share/save-
Aufruf nach dem Nutzen am Ende. Gemini verwendet sein natives JSON-Schema,
Groq inzwischen das entsprechende geschlossene JSON-Schema mit `strict=true`.
Beide bekommen denselben Grundauftrag und Quelltext; dessen Hash wird
protokolliert. Groq: reasoning_effort=low, Autor-Ausgabe maximal 3.840 Tokens;
die Ausgabegrenze umfasst auch Reasoning. Schema erzwingt keine Faktenwahrheit.

Je Quellenpaket wird pro Autor genau ein Erstentwurf erzeugt, ohne automatische
Reparaturen oder Auswahl eines Best-of. Die zufaellige Zuordnung zu A/B steht
nur im Ergebnisbericht. Verdeckte Lesefassungen liegen unter `blind/`.
Beide Anbieter pruefen beide Texte mit denselben Quellen auf Fakten und Story;
die Autoren sind also auch Pruefer. Diese symmetrische Gegenpruefung ist eine
KI-Vorpruefung und ersetzt kein unabhaengiges menschliches Urteil.

Zusaetzlich: Schema, Wortbudget, CTA, Zahlen, Kategorie-Mindestwerte sowie
Ausfaelle, tatsaechlich antwortendes Modell und Tokenverbrauch erfassen.
Keine Lite-Ausweichmodelle in diesem Vergleich. Groq-Minutenkontingent wird
beruecksichtigt; vorhandene Projekt-Zugaenge entscheiden ueber Verfuegbarkeit.

Der kleine Schreibauftrag ist nicht der vollstaendige Tagesprompt. Er testet
das Schreiben fuer ein vorgegebenes Thema, nicht automatische Themenwahl,
Rankings, Langvideos oder fertige Videoqualitaet. Keine MP4, Telegram-Nachricht
oder Plattform-Veroeffentlichung wird durch diesen Workflow erzeugt.
Der Standardautor bleibt bis zur begruendeten Entscheidung unveraendert.

Umsetzung: `fabrik/autorenvergleich.py`; Quellenvorbereitung:
`pruefungen/vorbereiten_autorenvergleich.py`. Aktuell 15 neue Vergleichstests
plus ein Test fuer den einmaligen Termin, Gesamtsuite 180 Tests bestanden.
Anfangsversion: zwoelf neue / 176 insgesamt.
Gemessene Ausfaelle, erfolgreiche Einzelproben und verbleibende Grenzen:
[ERGEBNIS-2026-10-06.md](ERGEBNIS-2026-10-06.md). Noch kein belastbarer Sieger.
Eine Fortsetzung fuer 07.10.2026 nach dem Reset ist mit Datumsschutz geplant.
