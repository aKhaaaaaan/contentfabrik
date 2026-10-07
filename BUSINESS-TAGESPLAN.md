# Nutzerideen und Tagesproduktion, 07.10.2026

Die Telegram-Liste wurde im echten Themenlauf
[37618751907](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37618751907)
um **14:07 Berlin** gesichert und bestaetigt. Update-ID `597759583`.
Die Ueberschrift war faelschlich eine elfte Idee; sie ist entfernt und der
Parser ignoriert solche Listenueberschriften kuenftig. Originale unveraendert
archiviert: `themen/eingaenge/2026-10-07-business.json`.

## Vorrat

Aktiv **eine Business-Story pro Tag**. Neun recherchierbare Ideen reichen
fuer neun erfolgreiche Produktionstage; die zehnte braucht noch eine Quelle.
`geplant_ab` ist eine frueheste Bearbeitung, kein zugesagter Versandtermin.
Bei einem Fehlschlag bleibt die aelteste bereite Idee erhalten; nachfolgende
Ideen verschwinden nicht. Ungeklaerte Ideen blockieren die bereiten nicht.

| Reihenfolge | Thema / Rechercheauftrag | Zustand |
|---|---|---|
| 1 | WeWork: Gruendung, Expansion und Folgen des Wachstums | Quelle abgerufen |
| 2 | Volkswagen: Dieselgate und seine Folgen | Quelle abgerufen |
| 3 | Netflix: DVD-Verleih, Streaming und Entwicklung | Quelle abgerufen |
| 4 | Enron: Aufstieg und Zusammenbruch | Quelle abgerufen |
| 5 | Yahoo: Wachstum, Uebernahmen und Verkauf | Quelle abgerufen |
| 6 | Starbucks: Gruendung, Expansion und Schultz | Quelle abgerufen |
| 7 | AOL/Time Warner: der grosse Zusammenschluss | Quelle abgerufen |
| 8 | Tesla: Wachstum und Folgen oeffentlicher Aussagen | Quelle abgerufen |
| 9 | Airbnb: von der ersten Idee zum internationalen Unternehmen | Quelle abgerufen |
| 10 | Anonymer 22-Jaehriger / App / 700.000 Dollar im Jahr | Name und Originalquelle fehlen |

Alle neun Artikel wurden lokal erfolgreich mit jeweils 7.000 Zeichen abgerufen.
Datierte, zugeordnete Wikipedia-Snapshots in `themen/quellen`, maximal 24 Stunden
alt verwendbar; danach frisch abrufen. Attribution/Artikel-URL und CC-BY-SA-
Hinweis in den Dateien. **Das sind Quellenpakete, keine freigegebenen Skripte.**
Die Telegram-Hooks sind Hypothesen, keine bestaetigten Zahlen oder Ursachen.
9 Milliarden, 18 Monate, 40 Jahre, 50 Milliarden und Tweet-Verluste muessen
am konkreten Fall belegt oder aus dem fertigen Titel/Text entfernt werden.
Bei zwei genannten Beispielen ist ein konkreter Fall gewaehlt (Enron, Airbnb);
die urspruengliche Idee bleibt in `idee_original` erhalten.

Der Tagesworkflow respektiert `tagesziel` von 1 oder 2, auch beim manuellen
Start. Business aktuell 1. Zwei Videos teilen weiter dasselbe Tagesbudget;
dadurch ist die Herstellung von zwei freigegebenen Videos nicht garantiert.
Veroeffentlichung auf YouTube/TikTok bleibt im bisherigen Ablauf **manuell**;
der Tageslauf liefert gepruefte MP4s nach Telegram. Kein automatischer
Plattform-Upload eingeschaltet, keine Beispielthemen ungefragt eingereiht.

## Warum weiterhin keine neuen Videos ankamen

- AI Tools Explained: erster Tagesversuch verbrauchte 1620,47 Sekunden in
  der Skriptphase. Der Rest von 179,53 Sekunden lag unter der Versandreserve;
  spaetere Slots erzeugten daher kein AI-Video.
- Business: [37609036124](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37609036124)
  startete um 12:41 Berlin, endete ohne Skript/Film am 205-Sekunden-Limit.
  Quelle Samsung lag vor; danach Gemini-Timeouts und HTTP-Ausfaelle. Das ist
  trotz gruener Workflow-Anzeige ein gesperrter Produktionsversuch.
- Beide Starts zu den konfigurierten Cronzeiten sind in GitHub sichtbar.
  Ein kompletter erfolgreicher Film-/Versandlauf ist damit nicht bewiesen.
- Tageszeitbudget, Provider-Ueberlastung und echte Provider-Tagesquote sind
  verschiedene Fehler. Nach drei Business-Versuchen 1312,409 von 1800
  Sekunden verbraucht; kein Reset. GitHub-Monatsverbrauch war ueber den
  vorhandenen Zugang nicht abrufbar (HTTP 404); freie Restminuten nicht behaupten.

## Neue technische Korrekturen

1. Fester Artikel und frischer Quellensnapshot sparen Artikelzuordnung und
   Erstabruf. Bei Business-Illustrationsstil keine unnoetige Wikimedia-
   Fotosuche. Originale Figuren und passende gemalte Szenen bleiben Vorgabe.
2. Im Tageslauf darf reine Text-KI bei Gemini-Ausfall nach kurzem Versuch
   ueber den vorhandenen Groq-Zugang ausweichen. JSON-Schema, Wortbudget,
   Zahlen-/Faktencheck und Story-Gates bleiben bestehen. Medienpruefungen
   haben **keinen** Text-Ersatz. Fallback-Modell und Faktenpruefer dokumentieren.
3. Faktencheck startet mit Lite. Bei Groq als Haupt-Faktenpruefer nicht denselben
   Groq-Pruefer erneut als angeblich unabhaengigen Anbieter aufrufen. Dieser
   Fall hat keinen Anbieter-unabhaengigen Zweitcheck; das wird ehrlich markiert.
   Kein Qualitaetssieger aus dem noch unvollstaendigen Autorenvergleich abgeleitet.
4. Kleines Antwortbudget fuer Textpruefungen, begrenzte Groq-Wartezeit; keine
   Kontenrotation oder kostenpflichtige Tarifumstellung. Bei gutem Skript und
   knapper Restzeit optionale Story-Umschreibung stoppen und Film bauen.
5. `entwurf_cache.py`: bestandene Skriptfassung im Repository und Teilbau
   ueber Actions-Cache zwischen Runs behalten. Maximal sechs Stunden,
   gleiches Thema/Profil/Pruefcode und unveraenderte Skriptsignatur erforderlich.
   Bauarbeit verlaengert alte Faktenpruefungen nicht. Rendercache prueft die
   konkreten Audio-/Bild-/Code-Signaturen weiterhin. Nach Versand Entwurf erledigen.
6. AI Tools Explained erklaert eine belegte praktische Anwendung statt eines
   schwer belegbaren Rankings aus mehreren neuen Repos. Quellenabruf endet
   nach ausreichender Beschreibung; ohne belegte Quelle kein KI-Skript erfinden.

Groq-Funktionen sind technisch verfuegbar laut
[Modellkatalog](https://console.groq.com/docs/models) und
[Structured Outputs](https://console.groq.com/docs/structured-outputs).
Die konkreten Kontingente/Verfuegbarkeit gelten fuer das eingerichtete Konto;
ein erreichbarer Dienst beweist keine 10/10-Qualitaet. Google listet aktuelle
Modelle in seiner [API-Dokumentation](https://ai.google.dev/gemini-api/docs/models).

**252 lokale Regressionstests bestanden**, 8,729 Sekunden. Prompt `2026-10-07.4`. Neue Faelle:
Listenueberschrift, bereite/recherchierte/zukuenftige Ideen, Quellenalter und
Artikelbindung, Tagesziel, providerbezogener Text-Fallback, falsches Schema,
keine Vision-Umgehung, kein Aufruf nach Deadline, cachefaehiger Teilbau,
Thema-/Profil-/Hash-/Altersbindung und keine TTL-Verlaengerung durch Bauarbeit.
Nachweis: `pruefungen/ergebnisse/2026-10-07/tagesplan-fallback-tests.json`.
Diese Tests verwenden simulierte Dienste. Reale neue Film-/Versandergebnisse
separat nachtragen; 252 Tests sind kein Nachweis einer Videozustellung.

Linux-CI fuer Code-Commit `68c1ace` erfolgreich:
[37623020063](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37623020063),
einschliesslich Kompilierung und Node-Zeitplanchecks. Danach um **14:44 Berlin**
ein neuer echter Tageslauf aus der Nutzerwarteschlange gestartet:
[37623180283](https://github.com/aKhaaaaaan/contentfabrik/actions/runs/37623180283).
Kein Budget reset, keine Pilot-Vorlage, keine alte MP4 erneut gesendet.
Dieser Versuch endete **ohne Video**: der neue Groq-Ausweichweg lehnte den
zu grossen Skriptauftrag lokal ab, bevor irgendeine Groq-Anfrage gestellt wurde.
13 Sekunden statt langer Wiederholungen; Business danach 1324,719 von 1800
Sekunden verbraucht. Rund 475 Sekunden verbleiben, kein Budgetreset.

Korrektur: kompakter Groq-Skriptauftrag mit unveraenderten vollstaendigen
Quellen und konkreten Fakten-/Story-Reparaturauftraegen. Technische Renderer-
Regie gekuerzt. Der reale WeWork-Auftrag mit 7.000 Zeichen Quelle braucht
konservativ ca. 6.387 statt 9.242 Tokens einschliesslich Ausgabe-/Schemareserve
(Grenze 7.900). Eigene Regressionen pruefen genau diesen realen Auftrag und
das Erhalten eines bestehenden Entwurfs samt Reparaturhinweisen. Sichere
Fehlerdetails werden protokolliert, statt alle Ausfaelle pauschal zu verstecken.
Die API-Erreichbarkeit und eine fertige MP4 sind dadurch noch nicht bewiesen.
