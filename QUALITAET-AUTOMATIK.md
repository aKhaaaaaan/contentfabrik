# Qualitaet im normalen Automatiklauf bestaetigen

Start: 06.10.2026. Vom Nutzer beauftragt: "Ja dann legen wir los, oder?
macht es sinn?! und dokumentiere es auch". Die Plattform-Veroeffentlichung
bleibt manuell. Ziel ist 10/10; eine absolute Qualitaetsgarantie gibt es nicht.

## Ablauf der ersten Serie

Der erste normale Tageslauf wurde am 06.10.2026 um **10:14:44 Berlin**
mit `video.yml`, `kanal=alle` und leerem Thema gestartet:
[37434817863](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37434817863).
GitHub hat den Start angenommen; beim ersten Statusabruf lief die Produktion
noch. Dies ist ein Startbeleg, keine Fertigstellung oder Qualitaetsbestaetigung.
Die naechsten Laeufe werden durch die bestehenden Tageszeitplaene ausgeloest.

1. Je Kanal drei unterschiedliche Shorts aus dem **normalen Tageslauf**
   erzeugen: automatische Themenwahl, Quellen, Skript, Bildplan, Bilder, Ton,
   Video und Pruefung. Kein vorab von Hand ausgefuelltes Skript oder Bildplan.
2. Die bestehenden Zeitplaene und das gemeinsame Tagesbudget von 30 Minuten
   je Kanal weiterverwenden. Zunaechst ein Video je Kanal und Produktionstag;
   nicht sechs teure Produktionen gleichzeitig starten oder Budgets umgehen.
   Bei Kontingent-/Quellenproblemen dauert die Serie entsprechend laenger.
3. Bestehende gezielte automatische Korrekturen sind Teil des getesteten
   Prozesses und werden protokolliert. Manuelle Nachbearbeitung muss als
   solche erfasst werden; danach ist das Ergebnis kein unbearbeiteter
   Automatik-Erfolg. Manuelles Starten von `video.yml` mit leerem Thema ist
   zulassig: Inhalt und Regie entstehen trotzdem automatisch.
4. Bestandene Videos gehen wie bisher auf Telegram. Gesperrte Videos bleiben
   gesperrt; sofern vorhanden sind Video und Pruefungen als GitHub-Artefakte
   verfuegbar. Auch Ausfaelle vor dem Videobau zaehlen als dokumentierte
   Fehlschlaege, nicht als bestandene oder fertiggestellte Videos.
5. Nach drei unterschiedlichen Videos je Kanal Fehler gemeinsam auswerten,
   die groessten wiederkehrenden Probleme korrigieren und erneut testen.
   Keine gelungenen Einzelfaelle herauspicken und Fehlversuche verschweigen.
   Erfolgreicher Workflow-Status, KI-Note und menschliches Urteil getrennt halten.

Die manuell kuratierten, am 05.10. gelieferten Qwen-/Nintendo-Piloten gehoeren
nicht zu dieser Serie. Sie bleiben positive Gestaltungsreferenzen. Ihre
23/12 bzw. 24/14 Einstellungen/Motive sind Ist-Werte, keine neuen Zielwerte.

## Vollstaendige Sichtpruefung des fertigen Videos

Die Person, die prueft, sieht und hoert die **ganze konkrete MP4**. Eine
KI-Note, ein Kontaktbogen oder eine Skript-Lektuere ersetzt dies nicht.

| Pruefpunkt | Woran sich das Urteil orientiert |
|---|---|
| `hook` | Die ersten Sekunden wecken Interesse und sagen klar, was die Geschichte bringt. |
| `spannung` | Nachvollziehbarer roter Faden, neue Informationen, passende Wechsel und befriedigende Aufloesung; keine langweiligen Leerstrecken. |
| `bild` | Bilder passen zum gerade gesprochenen Inhalt; mehrere Bilder pro Sprechphase; lesbare Untertitel, keine leeren Hauptbilder oder unpassenden Wiederholungen. |
| `figur` | Originale Kanalfigur am Einstieg und sinnvoll wiederkehrend; Identitaet konsistent, lebendige gemalte Spielwelt, keine kopierten GTA-Figuren. |
| `stimme` | Verstaendliche Aussprache, natuerliche Betonung und passendes Tempo; keine Stoerungen oder abgeschnittenen Saetze. |
| `ton` | Passende Hintergrundmusik und gezielte Geraeusche; Stimme bleibt gut hoerbar, keine stoerenden Pegelspruenge. |
| `cta` | Like/share/save wird explizit gesprochen, kurz und sinnvoll nach der Aufloesung. |
| `fakten_technik` | Quellen und Behauptungen stimmen; keine erfundenen Tool-Ergebnisse; Bild, Ton, Schnitt und Ende ohne relevante Fehler. |

Ziel fuer vergleichbare Shorts: AI Tools Explained etwa **14-18 Motive**;
Business Origin Stories etwa **24 Einstellungen mit 18 Motiven**. Echte
unterschiedliche Materialien zaehlen; Zooms und Titelwechsel sind keine neuen
Motive. Eine passende Erzaehlung bleibt wichtiger als eine isolierte Zahl.

Die menschliche Frage lautet: **Wuerdest du dieses Video ohne Nachbearbeitung
veroeffentlichen?** Fuer jeden Pruefpunkt Ja/Nein und konkrete Befunde
festhalten. Eine numerische Nutzernote bleibt optional; keine Note erfinden.
KI- und Menschennote getrennt speichern und Abweichungen zur Verbesserung
des Kritikers und der Produktion nutzen. Das Ziel 10/10 ist kein Anlass,
Noten kuenstlich anzuheben. Der Versandfilter ab 7/10 bleibt unveraendert;
Telegram-Zustellung ist keine Plattform-Freigabe.

## Konsistenz anschliessend bestaetigen

Als praktischen Kontrollpunkt **zehn aufeinanderfolgende unterschiedliche
Shorts je Kanal**, die alle technischen/redaktionellen Filter bestehen und
menschlich vollstaendig angesehen sowie ohne Nachbearbeitung fuer
veroeffentlichbar befunden wurden. Die ersten drei duerfen dazu zaehlen.
Ausfall, Sperre, Ablehnung, Nachbearbeitung oder fehlende Sichtpruefung
unterbrechen die im Protokoll bestaetigte Folge. Bewertung kann nachgetragen
werden; ein noch nicht angesehenes Video ist bis dahin kein bestaetigter Erfolg.

Geaenderter Produktionscode oder geaendertes Kanalprofil beginnen die Folge
neu. `produktionsversion` ist der SHA256-Fingerabdruck von `fabrik/*.py` und
dem Kanalprofil; reine Verlauf-/Dokumentations-Commits resetten ihn nicht.
Prompt-Version, Commit und vollstaendige KI-Pruefung werden ebenfalls gespeichert.
Lernregeln entwickeln sich weiter; der Fingerabdruck erfasst keine externen
Modellwechsel oder Lernregel-Aenderungen. Nach wesentlichen Aenderungen dort
ebenfalls eine neue Bestaetigungsserie anlegen und getrennt auswerten.

Zehn Erfolge sind ein Kontrollpunkt, keine statistische Garantie. Auch danach
wird **kein Upload automatisch aktiviert**. Eine spaetere Verbindung zu
YouTube/TikTok ist eine eigene Umsetzung. Shorts beweisen keine Langvideo-
Qualitaet: Langvideos separat testen, mit Aufmerksamkeitsbogen ueber die ganze
Laenge und gesprochenem CTA nach dem Einstieg sowie am Ende.

## Technik und Bedienung

`fabrik/qualitaetsserie.py` wird in `video.yml` nach dem Produktionsschritt
mit `if: always()` aufgerufen. Es speichert auch Fehlschlaege. Daten stehen
dauerhaft in `verlauf/qualitaetsserie.json`; ein Einzellauf-Protokoll liegt
zusaetzlich im Video-Artefakt als `ausgabe/qualitaetsserie.json`. Der bestehende
Sicherungsschritt pusht den Verlauf seriell mit Themen/Lernen nach `main`.
MP4-Artefakte haben weiterhin drei Tage Aufbewahrung: rechtzeitig herunterladen,
wenn sie nicht bereits auf Telegram vorliegen. Pruefbefunde und Hash bleiben
im Verlauf. Vollstaendige Aufbewahrung aller MP4s ist damit nicht eingerichtet.

Status ohne API-Zugriff:

```powershell
python fabrik/qualitaetsserie.py status
```

Manuelles Urteil als JSON-Datei anlegen und dem konkreten Lauf zuordnen:

```json
{
  "video_sha256": "exakter Hash aus dem Laufprotokoll",
  "pruefer": "Nutzer",
  "vollstaendig_angesehen": true,
  "ohne_nachbearbeitung": true,
  "veroeffentlichbar": true,
  "note": null,
  "pruefpunkte": {
    "hook": true, "spannung": true, "bild": true, "figur": true,
    "stimme": true, "ton": true, "cta": true, "fakten_technik": true
  },
  "befunde": "Tatsaechliche Beobachtungen und Nutzerfeedback hier eintragen."
}
```

Dieses Beispiel ist **keine bereits erfolgte Nutzerbewertung**. Werte nur
nach tatsaechlicher Sichtung setzen, Schwachpunkte ausdruecklich `false`.

```powershell
python fabrik/qualitaetsserie.py bewerten "RUN_ID.ATTEMPT:KANAL" "urteil.json"
```

Urteil danach gezielt uebernehmen/committen. Fehlende Pflichtfelder, falscher
Datei-Hash und ungueltige Noten werden abgelehnt. CLI-Aufruf schickt nichts
an Telegram oder Plattformen. Konkretes Feedback ausserdem wie bisher in die
wirksamen Lernregeln aufnehmen; der Serienstatus alleine trainiert kein Modell.

Tests: `pruefungen/test_qualitaetsserie.py` prueft unter anderem Trennung von
KI/Mensch, fehlendes Video, Hash-Zuordnung, doppelte Erfassung, gleiche Videos,
Fehlerunterbrechung, Versionswechsel und fehlende Upload-Freischaltung.
Testdateien simulieren MP4-Inhalt/Urteile; sie beweisen keine echte Videoqualitaet.

## Pruefnachweis der Umsetzung, 06.10.2026

Lokal unter Windows: `python -m unittest discover -s pruefungen -v`
bestand **164 Tests** (6,659 s, Exit 0), inklusive zehn neuer Tests fuer die
Serie. `python -m compileall -q fabrik pruefungen` bestand (Exit 0).
`node pruefungen/zeitplan.mjs` bestand fuenf Pruefungen (Exit 0).
`git diff --check` ohne Fehler. Die Zeitplan-Tests simulieren GitHub-Dispatches;
sie sind keine echten Videoproduktionen. Maschinenlesbarer Nachweis unter
`pruefungen/ergebnisse/2026-10-06/ergebnis.json`.
Nach Ergaenzung der Laufversuchs-ID wurden die zehn Serien-Tests nochmals
gezielt ausgefuehrt und bestanden (0,619 s, Exit 0).
