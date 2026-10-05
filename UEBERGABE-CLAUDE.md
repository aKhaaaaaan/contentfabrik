# Uebergabe an Claude – Contentfabrik

Stand: 05.10.2026, nach Uebernahme der Vorarbeit und der neuen Qualitaets-
und Formatverbesserungen. Dieses Dokument wird mit den Pilot-Ergebnissen
aktualisiert. Es enthaelt keine Zugangsschluessel.

## Nutzerauftrag und zugesagtes Ergebnis

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
- Alle erforderlichen Einzelkategorien mindestens **7/10**.
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

Noch tatsaechlich zu pruefen: echte Renderzeit bei Langvideo, Stimme/Ton,
Bildvariation, korrekte Wortzeiten, unabhaengige Gesamtkritik, neue
Korrekturwirkung, Zustellung und Kompressionsqualitaet.
Bei API-Kontingentproblemen Ursache dokumentieren statt Schwellen absenken.

## Dokumentation und sinnvolle Fortsetzung

### Gezielter Ersatzpilot: Nintendo-Karten

Der Nutzer hat weiterhin kein Video erhalten: `message_id:108` bestaetigt
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
