# Kostenlose KI fuer Skripte: gepruefter Stand 06.10.2026

Nutzerfrage: "Können wir denn nicht bessere ki für skript erstellung einsetzen? kostenlose?"
Kostenlose Alternativen sind vorhanden. Ein besseres Ergebnis fuer unsere
Kanaele ist damit noch nicht nachgewiesen; keinen pauschalen Sieger behaupten.

## Verfuegbare Kandidaten

| Kandidat | Offiziell dokumentierter Zugang | Stand im Tool |
|---|---|---|
| GPT-OSS-120B ueber Groq | Free Plan: 1.000 Anfragen/Tag, 200.000 Tokens/Tag, 8.000 Tokens/Minute laut Rate-Limits-Tabelle | Faktenpruefer in `fabrik/zweit.py`; neu als Testautor in `fabrik/autorenvergleich.py`, noch kein Standardautor im Tageslauf |
| Gemini 3.8 Flash | Ein-/Ausgabe im kostenlosen API-Tarif gelistet; Kontingent/Zugang fuer das konkrete Projekt entscheidet | Bereits zuerst in der Autor-Modellliste; Ausweichmodelle bis Flash-Lite moeglich |
| Gemini 2.5 Pro | Ein-/Ausgabe auf der offiziellen Preisseite als kostenlos gelistet; tatsaechlicher Zugang in unserem Projekt aktuell nicht bestaetigt | Nicht als Autor angebunden; fruehere Projektmessungen meldeten kein nutzbares Pro-Kontingent |

Quellen, am 06.10.2026 gelesen:
- [Groq Free Plan Limits](https://console.groq.com/docs/rate-limits)
- [Groq GPT-OSS-120B](https://console.groq.com/docs/model/openai/gpt-oss-120b)
- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)

Gratis-Zugang bleibt begrenzt. Eine kostenlose Chat-Oberflaeche oder frei
verfuegbare Modellgewichte sind kein Beleg fuer eine kostenlose, unbegrenzt
automatisierbare API. Keine kostenpflichtige Hochstufung eingerichtet.

## Gemessene aktuelle Schwachstelle

Der AI-Tageslauf `37434817863` nutzte laut Joblog ueberwiegend
`gemini-3.5-flash` (22 erfolgreiche Anfragen, rund 166.000 Eingabetokens).
Die Liste beginnt zwar mit 3.8 Flash, das garantiert keinen Zugriff darauf.
Das Skript blieb bei Story 7/10 / Aufloesung 6/10 gesperrt. Mehrere
Ueberarbeitungen fuehrten unbelegte Aussagen ein. Vorbereitete Piloten mit
besseren Bildern beweisen keine bessere automatische Skriptproduktion.

## Beauftragter Vergleich: gebaut und gestartet

GPT-OSS-120B als zusaetzlichen Autor testen, anstatt ungeprueft die taegliche
Produktion umzustellen. Je Kanal drei identische Quellenpakete fuer beide
Autoren verwenden: gleiche Fakten, Laenge, Stil-/CTA-Vorgaben und Aufgaben.
Die Modelle duerfen nicht unterschiedliche Themen/Quellen erhalten, wenn
wir ihre Schreibqualitaet vergleichen wollen.

Beide Fassungen mit Quellen/Zahlen pruefen und anonymisiert menschlich
beurteilen: Klarheit des Einstiegs, Aufloesung, Faktenstabilitaet, gesprochener
Rhythmus, Wortbudget und vollstaendiger CTA. KI-Noten nur als Zusatzsignal.
Ausfaelle, Laenge, Tokens und Reparaturbedarf mitprotokollieren. Das Modell,
das den Text geschrieben hat, soll nicht allein seinen Sieger bestimmen.
Erst bei wiederholter Verbesserung den Standardautor je Kanal festlegen;
ein hoeherer Einzelwert ist kein Nachweis dauerhafter Ueberlegenheit.

Der Nutzer hat den Vergleich beauftragt. Umsetzung und eingefrorene Quellen:
[vergleiche/autoren/README.md](vergleiche/autoren/README.md). Sechs Themen,
je zwei Erstentwuerfe und zwei verdeckte KI-Pruefer pro Text. Kein Best-of
oder Reparaturvorteil fuer einen Autor; tatsaechliches Modell und Ausfaelle
werden gespeichert. Identischer Grundauftrag, anbieterabhaengige Schema-
Uebermittlung. Zwoelf neue Tests bestanden, Gesamtsuite 176 Tests, auch auf
GitHub erfolgreich: Run `37441590949`, Commit `b6ae530`.

Echter Start des Vergleichs am 06.10. um 11:14:29 Berlin:
[Run 37441593314](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37441593314).
Gemessener Stand: [ERGEBNIS-2026-10-06.md](vergleiche/autoren/ERGEBNIS-2026-10-06.md).
Erste Serie: zwoelf Ausfaelle. Spaetere Einzelproben lieferten je einen
Qwen-Entwurf, aber keinen freigegebenen Text. Gemini meldete danach leeres
Autoren-Tageskontingent; 2.5-Ausweichprobe ebenfalls ohne nutzbaren Zugang.
Groq lieferte mit Strict-Schema und angepasstem Reasoning-/Ausgabebudget
einen vollstaendigen Diagnoseentwurf. Das ist noch kein Qualitaetsgewinn. Fortsetzung fuer 07.10.
um 09:17 Berlin geplant, Start kann durch GitHub verzoegert werden.
Keine menschliche Bewertung vorwegnehmen und keinen Sieger aus zwei Proben
ableiten. Die gepruefte 2.5-Preisliste bleibt korrekt; Projektzugang fehlte.
Der normale Tageslauf laeuft weiterhin mit der bestehenden Gemini-Anbindung.
Der Vergleich verbraucht vorhandene kostenlose API-Kontingente, erzeugt aber
keine Videos. Der fruehere Kommentar in `zweit.py`, es gebe keine eindeutig
bessere kostenlose Alternative, war ohne lokalen Autorenvergleich nicht
belastbar und wurde entsprechend korrigiert.

Die vom Nutzer zusaetzlich beauftragte Recherche fuer die ganze Pipeline
steht in [KOSTENLOSE-PIPELINE.md](KOSTENLOSE-PIPELINE.md), einschliesslich
Bild/Video, Stimme, Musik/FX, Untertiteln, Hardware und API-Grenzen.
