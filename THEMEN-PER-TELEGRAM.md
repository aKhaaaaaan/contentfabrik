# Eigene Themen fuer Contentfabrik

Stand: 07.10.2026. Eigene Ideen im **gleichen Telegram-Bot** schicken, der
die Videovorschauen sendet. Es gibt derzeit kein Dashboard zur Themeneingabe;
die vorhandene Website ist eine Informationsseite.

## Neu 08.10.2026: Befehls-Bot (Start/Status sofort)

Ein **zweiter** Bot nur fuer Befehle, beantwortet vom Cloudflare-Worker
`contentfabrik-zeitplan` innerhalb von Sekunden (der Videobot liest nur alle 4 h):
`Start` (beide Kanaele), `Start Business`, `Start KI`, `Status`, `Abholen` (Feedback/Themen aus dem Videobot sofort verarbeiten).
`Status` zeigt den Gesamtfortschritt in Prozent (geschaetzt: je Kanal
Einrichtung 0-10 %, Produktion 10-90 % nach Zeit bei max. 30 Min, Sichern
90-100 %), den aktuellen Schritt und schon fertige Kanaele. Nur der eigene Chat
(`TG_CHAT_ID`) darf starten; hoechstens 6 manuelle Laeufe am Tag; ein laufender
Lauf wird nicht doppelt gestartet. `/start` beim ersten Oeffnen startet nichts.
Einrichtung: Kopf von `cloudflare/zeitplan-worker.js`. Tests: `pruefungen/befehlsbot.mjs`.
Genauere Prozente (z. B. „Bild 14 von 25") brauchen spaeter einen Cloudflare-KV-Speicher.

## Neu 07.10.2026 abends (Claude)

**Eigenes Skript** - erste Zeile Kanal und Thema, darunter dein Text (40-900 Woerter,
auch Deutsch; erzaehlt wird Englisch):

```text
Skript Business: Wie WeWork scheiterte
WeWork wollte Bueros wie Software verkaufen ...
```

Claude behaelt Hook, Reihenfolge und Wortlaut, soweit die Quellen es tragen; nur
widerlegte/unbelegte Aussagen werden ersetzt. Fakten-, Story- und Videopruefung
laufen unveraendert.

**Video-Link** (YouTube, YouTube Shorts, TikTok), optional mit Kanal davor:

```text
Business: https://www.youtube.com/shorts/...
```

Titel und Kanal kommen ueber die offizielle, kostenlose oEmbed-Schnittstelle
(live geprueft 07.10.). Das fremde Video wird NICHT heruntergeladen oder
abgeschrieben (Urheberrecht, YouTube-Regeln); der Titel wird ein Rechercheauftrag.
Instagram braucht einen Meta-Zugang - der Bot bittet dann um das Thema als Text.

**Bewerten unter jedem Video:** Knoepfe ✅ Gefaellt / ❌ Ablehnen / Note ≤4-10.
Antwort (Wischen) auf das Video = Feedback genau zu diesem Video. Ablehnen
(oder Note ≤4) sperrt die Datei fuer erneuten Versand. Abholung mit dem
Themenlauf alle vier Stunden; die Bestaetigung kommt danach. Das ist ein
Schnellurteil, keine vollstaendige Sichtpruefung der Qualitaetsserie.
Code: `fabrik/bewertung.py`, `fabrik/themen.py`; Tests `test_bewertung.py`,
`test_telegram_eingang.py`.

Eine einzelne Idee:

```text
Business: Wie LEGO aus einer Holzwerkstatt entstand
```

Eine Liste, zum Beispiel zehn Ideen in **einer Nachricht**:

```text
Business:
1. LEGO
2. Nike
3. IKEA
4. Adidas
5. Netflix
6. McDonald's
7. Starbucks
8. Sony
9. Nintendo
10. Samsung
```

Dies ist ein Formatbeispiel, keine eingereihte Produktion oder Themenempfehlung.
Markennamen durch die eigenen Ideen ersetzen. Ein konkreter Blickwinkel ist
ebenfalls moeglich. Nummern und Aufzaehlungszeichen sind optional. Maximal
25 Ideen je Nachricht, maximal 200 Zeichen je Idee; eine ungueltige Liste
wird insgesamt zurueckgewiesen statt still abgeschnitten.

`Business:` ordnet Business Origin Stories zu; `KI:` ordnet AI Tools Explained
zu. Beide Kanal-Praefixe funktionieren auch fuer zehn einzelne Nachrichten.
Die eindeutige Zuordnung braucht keine KI-Anfrage. `Feedback:` speichert
Rueckmeldungen zum Lernen; es ist kein Themenauftrag. `hilfe` zeigt die Bedienung.

## Was danach passiert

Der Themenworkflow holt Nachrichten alle vier Stunden ab. Cloudflare ist auf
`7 */4 * * *` **UTC** eingestellt: am 07.10. in Berlin 02:07, 06:07,
10:07, 14:07, 18:07 und 22:07. Der GitHub-Ersatzzeitplan kann verspaetet sein.
Gespeicherte Zeitplaene beweisen noch keinen erfolgten Cron-Start; den echten
Betriebsnachweis separat kontrollieren. Telegram bestaetigt die Aufnahme erst
nach erfolgreicher Sicherung der Warteschlange in GitHub, nicht sofort beim Tippen.

Jeder Kanal bearbeitet die aelteste eigene Idee zuerst. Telegram-Themen haben
Vorrang vor automatischer Themenwahl. Die Liste startet weder zehn parallele
Produktionen noch zehn Videos am selben Tag. Quellen, Tagesbudget und alle
Qualitaetspruefungen gelten weiterhin; eine eingereihte Idee garantiert kein Video.

Ein fehlgeschlagenes Skript, ein Baufehler, eine Qualitaetssperre oder ein
Zustellfehler entfernt die Idee **nicht**. Erst nach erfolgreicher Telegram-
Videozustellung wird genau der verwendete Eintrag entfernt. Ein manuell ueber
GitHub vorgegebenes Thema und ein Pilot leeren die Telegram-Warteschlange nicht.
Noch nicht eingebaut: Telegram-Befehle zum Umordnen/Loeschen und Dashboard-
Bearbeitung. Als `recherche` markierte Ideen und noch nicht faellige Themen
werden jetzt uebersprungen. Ein fehlerhaftes, weiterhin `bereit` markiertes
Thema bleibt erhalten und braucht bei dauerhafter Ungeeignetheit eine Korrektur.
Die echte Nutzerliste und ihr Tagesplan stehen in [BUSINESS-TAGESPLAN.md](BUSINESS-TAGESPLAN.md).

## Umsetzung und Grenzen fuer Claude

- `fabrik/themen.py`: Listenparser, Kanalzuordnung, persistierter Telegram-
  Offset und Bestaetigungsausgang in `themen/telegram.json`. Update-IDs verhindern
  eine doppelte Aufnahme bei erneutem Abruf. Nachrichten aus fremden Chats
  werden ignoriert. Vor erfolgreichem Git-Push keine neue Lesebestaetigung.
- `.github/workflows/themen.yml`: abholen, Repository sichern, Nutzer bestaetigen,
  Bestaetigungsstand sichern. Ein Pushfehler stoppt vor der Telegram-Bestaetigung.
- `fabrik/lauf.py`: `nehmen()` liest nur; `erledigen()` folgt auf erfolgreichen
  Versand. Die Workflow-Sicherung persistiert die verbleibende Warteschlange.
- Bei Abbruch nach Telegram-Versand, aber vor Sicherung des Bestaetigungsstands,
  kann eine Aufnahmebestaetigung wiederholt werden. Es wird keine Exactly-once-
  Zustellung versprochen. Keine Zugangsdaten in diesen Dateien speichern.
- Tests in `pruefungen/test_themen_budget.py`, `test_telegram_feedback.py` und
  `test_betrieb.py`: Zehnerliste ohne KI, Reihenfolge, Update-Deduplizierung,
  ungueltige Listen, Speicher-/Telegram-Fehler, Sicherung vor ACK und Entfernung
  erst nach erfolgreichem Versand. Die Tests nutzen simulierte Telegram-Antworten.

## Trend-Check (ab 10.10.2026)

Eingereichte Themen werden nicht mehr stur der Reihe nach gebaut. Vor jedem Tageslauf
bewertet `fabrik/trendcheck.py` jedes offene Thema (Business zusaetzlich die gestern
meistgelesenen Firmen auf Wikipedia):

- YouTube: Ausreisser der letzten 30 Tage zum Begriff (Aufrufe / Kanaldurchschnitt)
- Wikipedia: Aufwind (letzte 2 Tage gegen Median der 4 Wochen davor) - nicht die Groesse
- Google Trends: Begriff steht heute in den US-Tagestrends oder deren Schlagzeilen

Eigene Themen bekommen +1 Punkt Bonus. Unter 1,5 Punkten Trendsignal bleibt ein Thema
liegen; dann waehlt der Kanal frei aus aktuellen Trends. Faellt jede Quelle aus, gilt die
alte Reihenfolge. Suchbegriff: Feld `trend_suche`, sonst `wikipedia`, sonst das Thema.
Der Grund steht im Telegram-Video („Warum heute") und in `verlauf/trendcheck/`.
Live-Vorschau: Workflow `themen` manuell starten. Auch der naechtliche Skript-Vorrat
(`vorrat.py`) schreibt die Themen in Trend-Reihenfolge; der Videolauf nutzt denselben
Tagesstand aus `verlauf/trendcheck/`.
