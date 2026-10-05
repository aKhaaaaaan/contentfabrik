# KI-Prompts und Medienqualitaet

Stand: 05.10.2026. Vorlagenversion: `2026-10-05.6`.
Die gemeinsamen Auftraege stehen in [fabrik/prompts.py](fabrik/prompts.py).
Skript und fertige Video-Kritik speichern die verwendete Version, damit
spaetere Vergleiche nachvollziehbar bleiben.

Der Faktencheck erhaelt bei Renderer-Skripten die gesprochenen Aussagen,
Titel und Beschreibung. Illustrative Regie und Stock-Suchbegriffe werden
separat visuell geprueft und nicht als historische Behauptung ausgegeben.
Eine redaktionelle Pilotvorlage durchlaeuft dieselbe echte Fakten- und
Storypruefung wie ein KI-Entwurf; gespeicherte Noten werden vorher verworfen.

## Welche KI welche Aufgabe bekommt

| Baustein | Modell/Werkzeug | Verbesserter Auftrag |
|---|---|---|
| Kurz-/Langvideo-Skript | vorhandene Gemini-Flash-Auswahl | Formatgerechte Leitfrage, belegte Entdeckungen, Zwischenantworten und vollstaendige Aufloesung; Kapitel fuer Langvideos; natuerliche gesprochene Saetze |
| Mini-Doku | Gemini, separater Doku-Aufruf | Gemeinsame Quellen- und Sprachregeln; keine erfundene Krise, falls die Quelle nur eine echte Entscheidung oder Huerde belegt |
| Faktencheck | Gemini plus optional Groq GPT-OSS/Qwen | Jede konkrete Behauptung gegen Quellen; Zahlen, Einheiten, Zeitbezug und Einschraenkungen erhalten; genaue problematische Klausel und Korrektur nennen |
| Story-Redaktion | Gemini | Feste Notenskala; konkrete Schwaeche und umsetzbarer Vorschlag mit denselben Fakten; keine erfundenen Zuschauerprognosen |
| Fotos und Stockclips | Gemini mit Vorschaubildern | Passender Gegenstand, Person, Ort und Epoche; brauchbarer Ausschnitt im ausgewaehlten Format 9:16/16:9; falsches Material ablehnen statt nach Schoenheit auswaehlen |
| Werkzeug-Demos | Gemini | Praktisches Ergebnis des konkreten Werkzeugs; lesbar auf dem Handy; keine Logos oder Benchmark-Tabelle als Nutzennachweis |
| Illustrationen | Cloudflare FLUX.1 schnell / FLUX.2 klein 4B mit Figurenreferenz | Eine konkrete Szene, klare Handlung, passende Epoche, Bildaufbau mit Platz fuer Text, konsistente erfundene Figur, kontrolliertes Licht und lesbare Mittentoene |
| Bildkontrolle | Gemini | Tatsächliches Bild gegen Szene und gegebenenfalls Figurenreferenz; Inhalt, Anatomie, Schrift und Beschnitt pruefen; sichtbarer Fehler geht in den naechsten Bildauftrag |
| Fertiges Video | Gemini mit Video und Ton | Bild/Text/Ton gemeinsam beobachten; Aussprache, Untertitel, Timing, verdeckte Woerter, repetitive Effekte und Aufloesung pruefen; konkrete Zeitmarken und Korrekturen |
| Nachbesserung und Lernen | Gemini und gespeicherte Messergebnisse | Beanstandete Abschnitte und eine Eingriffsart je Runde; gleiche Quellenregeln wie beim Erstentwurf; einzelne Kritik nicht zum universellen Erfolgsrezept erklaeren |

Die Aufgabe des Autors und die des Pruefers bleiben getrennt. Die Video-Kritik
bekommt keine vorherige Story-Note, die ihr Urteil beeinflussen koennte.
Eine gute KI-Note belegt weder Aufrufe noch Zuschauerbindung.

Die Formatregeln in `fabrik/dramaturgie.py` gelten beim Schreiben und Pruefen.
Shorts starten konkret und liefern verdichtete Entdeckungen. Langvideos
entwickeln die Leitfrage ueber Kapitel, beantworten kleinere Fragen unterwegs
und fuehren neue Konsequenzen ein. Originalmaterial hat Vorrang vor
Illustrationen. `bildmodus` steuert die Auswahl; optionale `bildtext`-Akzente
kommen ausschliesslich aus dem gesprochenen Abschnitt und folgen dessen
Wortzeiten. Die Freigabe verlangt auf aktuellen Nutzerwunsch Gesamtwert
mindestens 7 fuer Skript und Video, jede Kategorie mindestens 7,
keine offenen mittleren/schweren Probleme
und bestandene Fakten/Technik. Die Notenskala bleibt absolut; die gewuenschte
Schwelle ist kein Auftrag, Bewertungen hochzusetzen.

## Konkrete Aenderungen an den Prompts

- Der Autor unterscheidet Open Source, herunterladbare Gewichte, kostenloses
  Hosting und freie kommerzielle Nutzung. Eine Lizenz ist kein Beleg fuer
  einen kostenlosen Onlinedienst.
- Likes und Sterne auf verschiedenen Plattformen werden nicht als objektiver
  Leistungsvergleich ausgegeben. Die Rangfolge aus dem Code bleibt erhalten.
- Der Einstieg hat einen kurzen ersten Satz. Die Aufloesung kommt vor
  hoechstens einer kurzen Handlungsaufforderung; keine widerspruechlichen
  Follow-/Save-/Loop-Pflichten und kein kuenstlicher Satzabbruch.
- Die Bildbeschreibung nennt Gegenstand, sichtbare Handlung, Epoche,
  Bildausschnitt und Licht. Eine historische Werkstatt bekommt passende
  Requisiten, nicht automatisch eine heutige Fabrik.
- Eine Illustration wird nicht als dokumentarischer Nachweis eingesetzt.
  Beim zweiten Versuch bleiben alle Szenendetails erhalten; der beobachtete
  Bildfehler wird ergaenzt. Eine ausgefallene Bildkontrolle gibt kein Bild frei.
- Quellen, Entwuerfe, Bildbeschriftungen und gelerntes Feedback werden als
  Eingabedaten behandelt. Darin enthaltene Anweisungen sollen die Aufgabe
  nicht ueberschreiben.

Beispiel fuer eine illustrative Szene (kein behauptetes historisches Foto):

> A worker assembling a bicycle in a small workshop around 1900, medium shot,
> period tools on a wooden bench, warm window light, uncluttered upper and lower frame.

Der FLUX-Auftrag ergaenzt dazu den gemeinsamen gemalten Plakatstil,
Figurenkonsistenz und die Komposition. Er verwendet die unterstuetzten
Parameter statt erfundener Negative-Prompt-/Qualitaets-Schalter.

Ausdruecklicher Nutzerwunsch: GTA-artige urbane Comic-/Spielplakat-Anmutung,
mit eigenstaendigen Figuren, markanten Konturen, gemalter Schattierung und
cineastischem Licht. Keine GTA-Charaktere, charakteristischen Outfits, Logos
oder konkreten Spielszenen kopieren. Die Promptfassung `2026-10-05.4`
beschreibt den Look allgemein und prueft erkennbare kopierte Spielfiguren.

## Stimme, Musik und Geraeusche

Jedes Video fordert ausdruecklich zum **Liken, Teilen und Speichern** auf.
Shorts bekommen eine kurze Zeile nach der Aufloesung nahe dem Ende;
Langvideos eine nach Hook/erstem Nutzen am Anfang (20–30 Sekunden) und
eine nach der Aufloesung am Ende. Alle drei Aktionen werden jeweils genannt,
ein Abo-Aufruf allein reicht nicht. Formulierungen bleiben natuerlich und
knapp (moeglichst maximal 12 englische Woerter) und zaehlen zum Wortbudget.
Der Aufruf ist verpflichtend in der gesprochenen Erzaehlung, zum Beispiel
"Be sure to like, share and save this video."; nicht nur als Einblendung
oder Beschreibung und nicht bedingt auf "falls es euch gefallen hat".
Die gemeinsame Regel steht in `dramaturgie.interaktion()` und wird auch
von Story-/Video-Pruefung und dem separaten Doku-Editor verwendet.

Kokoro bekommt Sprechtext, ausgewaehlte Stimme, Geschwindigkeit und Sprache;
es hat im verwendeten Aufruf keinen freien Regie-Prompt. Die vorhandenen
Stimmen bleiben erhalten. `bm_george` und `bf_emma` verwenden jetzt `en-gb`,
`am_michael` verwendet `en-us`. Klammer-Regie, SSML oder Emotionstags sollen
nicht im gesprochenen Text stehen. Zu lange Entwuerfe werden vor dem
Faktencheck gekuerzt. Eine automatische Tempoerhoehung bleibt bei maximal
1,25; ein bereits explizit gewaehltes hoeheres Tempo wird dabei nicht erhoeht.

Musik und Soundeffekte werden derzeit gesucht beziehungsweise aus den
vorhandenen CC0-Dateien gemischt, nicht von einer Audio-KI generiert:

- Der Skript-Autor liefert passende Suchbegriffe fuer dezente Instrumentalmusik.
  Sie folgen Szene, Epoche, Stimmung und Erzaehlkurve; keine beliebige
  Dauerspannung oder pauschale Action-Musik wegen des Bildstils.
  Die Suche ergaenzt `instrumental` und vermeidet eindeutige Vocal-/Sprach-Titel.
  Metadaten koennen Gesang nicht sicher ausschliessen; die fertige Tonspur
  wird deshalb auch im Video-Pruefer angehoert.
- Die Hintergrundmusik wird vor der Mischung im Pegel angeglichen und am
  Ende ausgeblendet. Die bestehende Absenkung unter der Stimme bleibt aktiv.
- Effekte werden gekuerzt, mit kurzen Ein-/Ausblendungen versehen und leiser
  eingepegelt. Doppelte oder sehr dichte Whooshes werden entfernt.
- Ein Riser endet am Akzent, auch wenn sein Original laenger als die Zeit
  davor ist. Ueberlagerungen bekommen eine begrenzte gemeinsame Spitze.

Die Video-Kritik beurteilt jetzt ausdruecklich die inhaltliche/emotionale
Soundpassung. Der Renderer verwendet derzeit ein Musikbett pro Video;
automatische Musikwechsel je Kapitel sind noch nicht implementiert.

Stockvideos verwenden die beste angebotene `large`-/`medium`-/`small`-Datei
statt grundsaetzlich die mittlere Fassung. Ein Cache fuer kleinere Dateien
wird dabei nicht fuer dieselbe hoehere Qualitaet ausgegeben. Das kann mehr
Downloadvolumen und Speicher benoetigen. Die letzte Video-Pruefung und das
Zeitbudget bleiben verbindlich.

## Modellvorgaben und Grenzen der Kontrolle

Gemini 3.x verwendet die Sampling-Standardwerte statt pauschal sehr niedriger
Temperaturen. Medien stehen vor dem konkreten Auftrag; PNG/JPEG/WebP werden
mit dem passenden Medientyp uebergeben. Google empfiehlt klare Aufgaben,
konkreten Kontext und strukturierte Ausgaben und warnt bei Gemini 3.x vor
heruntergesetzten Sampling-Werten. Quellen:
[Google Prompt-Design](https://ai.google.dev/gemini-api/docs/prompting-strategies),
[Google Video-Verstaendnis](https://ai.google.dev/gemini-api/docs/video-understanding).

FLUX.1 schnell behält acht Schritte innerhalb des dokumentierten Maximums.
FLUX.2 klein 4B hat bei Cloudflare vier feste Schritte; Referenzbilder werden
nur fuer den Upload auf weniger als 512 Pixel je Seite verkleinert, die
Projektdatei bleibt erhalten. Die Ausgabe ist mit Referenz 768 × 1360 statt
768 × 1024, wodurch weniger vom Motiv im Hochformat abgeschnitten wird.
Im optionalen Langformat verwendet derselbe Referenz-Aufruf 1360 × 768
und eine Landschaftskomposition. Die Bildkontrolle kennt das gewaehlte
Format; Fotos und Demos werden vollstaendig eingepasst, Stockclips beschnitten.
Quellen: [Cloudflare schnell](https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/),
[Cloudflare klein](https://developers.cloudflare.com/changelog/post/2026-01-15-flux-2-klein-4b-workers-ai/).

Weitere technische Referenzen:
[Kokoro-Aufruf](https://github.com/thewh1teagle/kokoro-onnx/blob/main/src/kokoro_onnx/__init__.py),
[Pixabay-Dateivarianten](https://pixabay.com/api/docs/).

Lokale Pruefungen kontrollieren API-Vertraege, Bildfreigabe, Cache,
Skriptlaenge und echte erzeugte Effekt-WAV-Signale mit ersetzten Downloads
und Modellantworten. Sie beweisen keine bessere Modellantwort. ffmpeg-Mix,
Aussprache und optische Wirkung muessen im vorbereiteten Cloud-Pilot mit
dem fertig erzeugten Video beurteilt werden. Dafuer fehlt in dieser Sitzung
weiterhin der nutzbare GitHub-/Produktionszugang; ein echter Lauf wurde
nicht ausgefuehrt.
