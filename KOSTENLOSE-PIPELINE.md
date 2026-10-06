# Kostenlose Werkzeuge fuer die gesamte Pipeline

Recherche und Abgleich mit dem vorhandenen Code: **06.10.2026**.
Nutzerauftrag: kostenlose KI-Werkzeuge fuer Skript, Bild, Video, Stimme,
Musik/Geraeusche und Bearbeitung pruefen. Ziel bleibt 10/10; ein neues Modell
oder eine KI-Note allein beweist keine bessere fertige Videoqualitaet.

Die folgende Auswahl ist unsere Einschaetzung fuer Contentfabrik, kein
anbieteruebergreifender Qualitaetsbenchmark. Kostenloses API-Kontingent,
offene lokale Modellgewichte und Gratis-Weboberflaechen sind unterschiedliche
Dinge. Kontingente, Projektzugang und Hardware bleiben entscheidend.

## Auswahl je Produktionsschritt

| Schritt | Sinnvolle Auswahl | Was ist kostenlos? | Entscheidung fuer unsere Pipeline |
|---|---|---|---|
| Themen und Quellen | Hersteller-READMEs/Modellkarten fuer KI; mehrere belegte Quellen fuer Firmenhistorie | Oeffentlich abrufbare Quelltexte; keine garantierte unbegrenzte Abrufrate | Quellen einfrieren, konkrete Aussagen belegen, Quellenumfang vor dem Schreiben pruefen; kein Modell ersetzt Recherche |
| Skript | **GPT-OSS-120B ueber Groq gegen Gemini Flash vergleichen** | Groq Free Plan; Gemini Free Tier nach Modell und Projekt | Echter Vergleich eingerichtet und gestartet, gleiche Quellen/Vorgaben, kein vorweggenommener Sieger |
| Fakten und Dramaturgie | Gemini und Groq als gegenseitige Pruefer, dazu vorhandene Zahlen-/Strukturpruefung | Dieselben begrenzten kostenlosen Kontingente | Urteile mit konkreten Belegen; Pruefer-Vorschlaege sind keine Quellen. Menschliche Bewertung bleibt erforderlich |
| Bildplanung | Gemini Flash; Lite fuer einfache Bildpruefungen | Kostenlos innerhalb des jeweiligen Kontingents | Szenen zuerst planen, dann Material erzeugen; Autor-Kontingent nicht fuer jede kleine Bildentscheidung verbrauchen |
| Originale Figuren und Illustrationen | **FLUX.2 klein 4B auf Cloudflare Workers AI** | Workers AI: 10.000 Neurons pro Tag, fuer alle Modelle gemeinsam | Bereits angebunden; Referenzbilder, eigener urbaner Illustrationsstil und echte Motivwechsel beibehalten |
| Alternative Bilder | FLUX.1 schnell lokal oder auf Cloudflare | Apache-2.0-Gewichte; Cloudflare-Kontingent | Kandidat fuer Hintergruende/Zwischenszenen. Kein nachgewiesener besserer Ersatz fuer konsistente Referenzfiguren |
| Echte Bild-zu-Video-Animation | **Wan2.2 TI2V 5B lokal** | Apache-2.0-Gewichte; eigene Rechenleistung erforderlich | Optionaler spaeterer Animationsvergleich. Offizieller 720p-Aufruf nennt mindestens 24 GB VRAM; keine kostenlose taegliche Cloud-API dadurch vorhanden |
| Erzählerstimme heute | **Kokoro-82M / ONNX** | Apache-2.0-Gewichte, auf CPU nutzbar | Bestehende Stimmen beibehalten; Aussprache, Pausen und Satzlaenge am fertigen Audio beurteilen |
| Ausdrucksvollere Cloud-Stimme als Kandidat | **Gemini 3.8 Flash TTS**, alternativ 2.5 Flash Preview TTS | Ein-/Ausgabe im Free Tier gelistet, Projektkontingent entscheidet | Fuer unseren Rechner leichter pruefbar als grosse lokale Stimmenmodelle; Stilsteuerung dokumentiert. Zuerst Hoervergleich und Worttreue testen, nicht schon eingebaut |
| Ausdrucksvollere Stimme als Kandidat | **Qwen3-TTS 1.7B CustomVoice/VoiceDesign** | Apache-2.0-Gewichte; offizieller lokaler Beispielcode nutzt CUDA | Anweisungen fuer Emotion/Prosodie und eigene Figurenstimmen sind interessant. Kein belegter Qualitaetsgewinn bei unseren Texten; GPU-/Laufzeitvergleich fehlt |
| Individuelle Hintergrundmusik | **ACE-Step 1.5** | MIT-Code und MIT-Modellgewichte; lokale Berechnung | Interessanter Kandidat fuer vorproduzierte Instrumentalbetten. Erst hoeren und passend zur Story freigeben; nicht bei jedem Tageslauf einen neuen GPU-Dienst voraussetzen |
| Musik und konkrete Geraeusche heute | Bestehendes Openverse, eigene Musik/FX; ergaenzend kuratierte Pixabay-Dateien | Frei lizenzierte Einzeldateien bzw. eigene Synthese | Bestehende lizenzgefilterte Openverse-Suche laeuft bereits. Eine kleine kuratierte Bibliothek verbessert Passung und Zuverlaessigkeit eher als zufaellige Tracks |
| Untertitel und gesprochener CTA | **faster-whisper / Whisper** | MIT, CPU-INT8 verfuegbar | Bereits fuer Untertitel genutzt. Zusaetzliche unabhaengige Transkription des finalen Tons ist der naechste sinnvolle Pruefschritt |
| Schnitt, Bewegung und Mischung | **FFmpeg plus vorhandener Szenenplan** | Freie Software, eigene CPU-Zeit | Bestehenden Renderer behalten; Erzaehlrhythmus, Musik-Ducking, passende FX und Motivvielfalt verbessern. Mehr Zooms sind nicht mehr Motive |
| Endkontrolle und Lernen | Bestehende Technik-/KI-Pruefung und Qualitaetsserie | Lokale Checks plus begrenzte KI-Kontingente | Fertige Datei vollstaendig ansehen/hoeren, Hash und Nutzerfeedback speichern; keine fiktiven Nutzernoten oder garantierte Zuschauerbindung |

## Primaerquellen fuer Zugang und Grenzen

**Schreiben:** [Groq-Modelle](https://console.groq.com/docs/models) und
[Groq-Free-Plan-Limits](https://console.groq.com/docs/rate-limits) listen
GPT-OSS-120B als Produktionsmodell mit 30 Anfragen/Minute, 1.000/Tag,
8.000 Tokens/Minute und 200.000/Tag. Qwen3.8-27B steht dort als Preview;
das ist kein belegter stabilerer Standardautor. [Gemini-Preise](https://ai.google.dev/gemini-api/docs/pricing)
listen unter anderem 3.8 Flash sowie 2.5 Pro mit kostenlosem Ein-/Ausgabetarif.
Der tatsaechliche Pro-Zugang unseres Projekts ist nicht bestaetigt. Im
heutigen Tageslauf antwortete ueberwiegend 3.5 Flash trotz neuerer Modelle
am Anfang der Modellliste. Der Autorenvergleich protokolliert deshalb das
tatsaechlich antwortende Modell. Details: [KI-MODELLE.md](KI-MODELLE.md).

**Bilder:** [Cloudflare-Preise](https://developers.cloudflare.com/workers-ai/platform/pricing/)
beschreiben 10.000 Neurons/Tag, Reset 00:00 UTC und fehlgeschlagene weitere
Operationen nach Ueberschreitung im kostenlosen Tarif. FLUX.2 klein 4B wird
mit 5,37 Neurons pro 512x512-Eingabekachel und 26,05 pro Ausgabekachel gelistet.
Das sind Kacheln, nicht pauschal Kosten je Bild; Referenzen, Groesse und
Wiederholungen zaehlen mit. Kontingent im Account messen, nicht eine feste
Bildanzahl garantieren. [Cloudflare-Endpunkt](https://developers.cloudflare.com/workers-ai/models/flux-2-klein-4b/)
ist dokumentiert. Die [originale 4B-Modellkarte](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B)
nennt Apache 2.0, mehrere Bildreferenzen und ungefaehr 13 GB VRAM fuer lokale
Nutzung. [FLUX.1 schnell](https://github.com/black-forest-labs/flux) ist eine
offene Apache-2.0-Alternative; das ist kein Beleg fuer bessere Figurenkontinuitaet.

**Video:** Die [originale Wan2.2-5B-Modellkarte](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B)
belegt Text-/Bild-zu-Video und Apache 2.0. Der dortige 720p-Aufruf mit
CPU-Offload benoetigt mindestens 24 GB VRAM. Das kann lebendige kurze
Zwischenszenen ermoeglichen, ist aber hier weder installiert noch getestet.
Keine Aussage ueber fehlerfreie Figurenidentitaet oder kostenlose Hosting-
Kapazitaet aus offenen Gewichten ableiten.

**Stimme:** [Kokoro-Modellkarte](https://huggingface.co/hexgrad/Kokoro-82M)
belegt die offene Apache-2.0-Basis.
[Gemini-Preise](https://ai.google.dev/gemini-api/docs/pricing) listen auch
3.8 Flash TTS und 2.5 Flash Preview TTS mit kostenlosem Ein-/Ausgabetarif.
Die [TTS-Anleitung](https://ai.google.dev/gemini-api/docs/speech-generation)
dokumentiert bei 3.8 eine Trennung von Sprechtext und Stil-Metadaten fuer
Tempo/Emotion. Modelllisting in unserem Projekt bestaetigt beide IDs, aber
Audioerzeugung und nutzbares Gratiskontingent wurden noch nicht getestet.
Das ist der bevorzugte **naechste kostenlose Stimmenvergleich** mit Kokoro,
weil dafuer keine eigene CUDA-GPU noetig ist. TTS ist ein eigener API-Aufruf;
die vorhandene Text-JSON-Anbindung produziert dadurch noch kein Audio.
[Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)
und die [CustomVoice-Modellkarte](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)
belegen offene Modelle und steuerbare Ausdrucksweise. VoiceDesign kann eine
eigene Stimme nach Beschreibung erzeugen; CustomVoice bietet vorgegebene
Stimmen mit Instruktionen. Kein Celebrity-Klon ist fuer unsere Originalfiguren
noetig. Eine kostenlose Anbieter-API oder identische Stimme zu Kokoro wurde
damit nicht bestaetigt.

**Musik:** [ACE-Step-Projekt](https://github.com/ace-step/ACE-Step-1.5),
[Modellkarte](https://huggingface.co/ACE-Step/Ace-Step1.5) und
[Hardware-Anleitung](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INSTALL.md)
belegen MIT und hardwareabhaengige Konfigurationen. Die kleine Turbo-Variante
kann mit Quantisierung/Offload auf deutlich kleineren GPUs als Video-Modelle
laufen; andere Varianten benoetigen mehr Speicher. Autoren-Werbeaussagen
ueber Ueberlegenheit sind kein eigener Hoerbenchmark. Fuer uns waeren
instrumentale, kanaltypische Betten sinnvoll; Gesang soll den Sprecher nicht
ueberlagern.

**Geraeusche und Bibliotheken:** [Pixabay Content License](https://pixabay.com/service/license-summary/)
erlaubt kostenlose Nutzung und Anpassung im Rahmen ihrer Bedingungen.
Die [oeffentliche Pixabay-API](https://pixabay.com/api/docs/) dokumentiert
Bild- und Videosuche. Eine entsprechende Musik-/Soundeffekt-API ist dort
nicht belegt: kuratierte Dateien mit Herkunft speichern, keine erfundene
Audio-Anbindung behaupten. Im vorhandenen Tool liefert `bauen.py:musik_holen`
schon Openverse-Musik mit CC0-/CC-BY-Filter; `ton.py` erzeugt eigene Musik
und FX als Alternative. Konkrete Tonpassung muss gehoert werden.

**Untertitel/Schnitt:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
dokumentiert MIT und CPU-INT8. [FFmpeg](https://ffmpeg.org/about.html) kann
Audio/Video bearbeiten und filtern. Beide werden bereits verwendet.
`bauen.py` gleicht erkannte Woerter fuer die Untertitel an den Skripttext an.
Diese angeglichenen Woerter sind deshalb kein unabhaengiger Nachweis dafuer,
dass der CTA wirklich hoerbar ist. Geplant: Rohtranskript aus der fertigen
MP4 vor jeder Textangleichung mit dem Solltext vergleichen; aktuell noch
keine solche neue Endton-Pruefung eingebaut.

## Angebote, die wir nicht als dauerhafte Gratis-Basis empfehlen

| Angebot | Gepruefter Grund |
|---|---|
| Hugging Face Inference Providers | [Preisquelle](https://huggingface.co/docs/inference-providers/pricing): Free Users erhalten derzeit 0,10 USD monatlich, Aenderungen vorbehalten. Experimentierguthaben, keine tragfaehige taegliche Video-Basis |
| Pollinations | [Aktuelles Original-README](https://github.com/pollinations/pollinations) beschreibt Pollen-Guthaben, Pay-as-you-go und API-Schluessel. Quests koennen Guthaben geben; kein bestaetigtes unbegrenztes Gratis-Angebot fuer unsere Tagesproduktion |
| OpenRouter-Free-Varianten | [Limits](https://openrouter.ai/docs/api_reference/limits) unterscheiden kostenlose Varianten, Tages-/Minutenkontingente und Accountstufen. Konkrete Grenzwerte wurden aus der aktuell ausgelieferten Tabelle nicht verlaesslich ausgelesen; keine veralteten Zahlen als garantiert uebernehmen. Groq ist bereits angebunden |
| MusicGen | [Originale Modellkarte](https://huggingface.co/facebook/musicgen-small): Code MIT, Modellgewichte CC-BY-NC 4.0. Deshalb fuer den kommerziell gedachten Kanal keine Standardempfehlung |
| Gratis-Webdemos allgemein | Eine nutzbare Webdemo belegt weder taegliche API-Kapazitaet noch automatische Verarbeitung. Ohne dokumentierten Zugang nicht als unbeaufsichtigte Produktionsabhaengigkeit einplanen |

## Reihenfolge fuer Contentfabrik

1. **Skriptproblem messen:** sechs Quellenpakete, je ein Erstentwurf von
   Gemini und GPT-OSS; gegenseitige verdeckte Pruefung, gleiche Fakten und CTA.
   Echter Start am 06.10. um 11:14:29 Berlin, GitHub-Run
   [37441593314](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37441593314).
   Methodik und Ergebnisse: [Autorenvergleich](vergleiche/autoren/README.md).
   Die erste Serie lieferte keine verwertbaren Entwuerfe. Diagnose und
   Korrekturen ermoeglichten spaeter je einen Qwen-Entwurf; beide sind noch
   nicht freigegeben. Geminis Autorenkontingent war danach erschoepft.
   Noch kein nachgewiesener Qualitaetssieger; Fortsetzung nach Reset geplant.
2. **Visuelle Staerken erhalten:** eigene Figuren im GTA-inspirierten urbanen
   Illustrationsstil, keine kopierten Spielcharaktere. AI Tools Explained:
   14-18 verschiedene Motive; Business Origin Stories: Ziel 24 Einstellungen
   mit 18 Motiven. Bilder passend zu mehreren Momenten je Skriptphase planen.
3. **Audio gezielt verbessern:** passende Instrumentalbetten und einzelne
   sinnvolle Geraeusche; unabhaengigen finalen CTA-/Sprachtest als naechste
   Erweiterung vorsehen. Gemini Flash TTS zuerst gegen Kokoro hoeren;
   Qwen3-TTS und ACE-Step zunaechst nur als lokale Kandidaten.
4. **Echte Animation spaeter pruefen:** auf diesem PC wurde am 06.10. nur
   Intel UHD Graphics erkannt, keine NVIDIA-CUDA-GPU. Der aktuelle normale
   GitHub-Lauf ist ebenfalls kein GPU-Renderer. Keine grossen GPU-Modelle
   herunterladen oder GPU-/Cloud-Kosten ohne konkreten Auftrag einrichten.
5. **Ergebnis menschlich bestaetigen:** KI-Skriptvergleich ist kein fertiger
   Videovergleich. Die bestehende Qualitaetsserie sammelt Tageslaeufe und
   menschliche Sicht-/Hoerurteile. Automatischer YouTube-/TikTok-Upload bleibt
   unangebunden; Telegram-Versand nach bestandenem Filter ist davon getrennt.

## Umsetzung und Grenzen dieser Aenderung

Neu gebaut: Quellen-Snapshots, kontrollierter Autorenvergleich, verdeckte
Lesefassungen, zwei KI-Pruefer, strukturierte Ausfall-/Verbrauchsberichte,
GitHub-Workflow mit manuellem Start/einmaligem Folgetermin und 15 Regressionstests. Bestehende Zugaenge
werden verwendet, keine neue kostenpflichtige Hochstufung eingerichtet.

Die Tagespipeline schreibt weiterhin mit ihrer bisherigen Gemini-Anbindung.
Gemini TTS, Wan, Qwen3-TTS und ACE-Step sind recherchiert, nicht eingebaut oder qualitativ
getestet. Die Recherche verspricht keine durchgehend kostenlose GPU-Cloud,
keine 100% fehlerfreien Videos und keine garantierte Zuschauerbindung.
Die konkreten Vergleichsergebnisse werden getrennt dokumentiert, damit
Claude Versuchsaufbau, gemessene Wirkung und Empfehlungen unterscheiden kann.

## Nutzerfrage: zweites Gemini-Konto fuer mehr Gratiskontingent?

Ein zweites Konto allein ist keine Empfehlung zur stabileren Pipeline.
[Googles Limit-Dokumentation](https://ai.google.dev/gemini-api/docs/rate-limits)
legt Kontingente pro Projekt statt pro API-Schluessel fest. Ein weiterer
Schluessel im selben Projekt erhoeht sie nicht. Tages-Anfragen werden um
Mitternacht Pacific zurueckgesetzt: am 07.10.2026 entspricht das 09:00 Berlin.
Ein Kontingent von null wegen fehlender Modellberechtigung wird dadurch
nicht automatisch nutzbar; das konkrete Projekt entscheidet.

Die [Google-API-Bedingungen, Abschnitt 2d](https://developers.google.com/terms)
untersagen die Umgehung dokumentierter API-Limits. Mehr Konten/Projekte fuer
dieselbe Pipeline zum Umgehen der Grenze empfehlen wir daher nicht.
Keine pauschale Aussage, dass getrennte legitime Anwendungen nie eigene
Projekte nutzen duerfen; es geht hier um die ausdruecklich vorgeschlagene
Umgehung fuer dieselbe Anwendung.

Empfohlen: Textaufgaben nach bestaetigtem Vergleich auf Groq verteilen,
Gemini-Kontingent fuer Bild-/Videoverstaendnis reservieren, unveraenderte
KI-Pruefergebnisse mit Text-/Quellen-/Prompt-/Modell-Hash wiederverwenden,
Reparaturschleifen begrenzen und bei leerem Tageskontingent pausieren.
Ein Schema-/Zahlen-/Wortbudgetfehler soll vor einer teuren KI-Runde auffallen.
Neue Pruefresultat-Caches und ein neuer Standardautor sind hier noch nicht
in die Tagesproduktion eingebaut. Qualitaetspruefungen nicht weglassen, um
Kontingent zu sparen. Kontingentfehler sind keine niedrige Qualitaetsnote.
