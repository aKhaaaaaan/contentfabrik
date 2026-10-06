# Einstieg fuer Claude

Bitte zuerst [UEBERGABE-CLAUDE.md](UEBERGABE-CLAUDE.md) und danach
[README.md](README.md), [PROMPTS.md](PROMPTS.md) und [KONZEPT.md](KONZEPT.md)
lesen. Die Uebergabe beschreibt die neuen Aenderungen, den aktuellen
Betriebsstand, Pruefungen und die noch offenen Arbeiten.

**Neuer Auftrag 06.10.2026:** Qualitaet im normalen taeglichen Automatiklauf
bestaetigen: zuerst drei unterschiedliche Shorts je Kanal, vollstaendig
menschlich pruefen, Fehler korrigieren, danach zehn bestaetigte Erfolge in Folge
je Kanal als Kontrollpunkt. Plattform-Uploads bleiben manuell. Keine kuratierten
Piloten als Automatik-Erfolg zaehlen. Ablauf, Rubrik und Bedienung stehen in
[QUALITAET-AUTOMATIK.md](QUALITAET-AUTOMATIK.md); echte Ergebnisse und getrennte
Sichtpruefungen stehen in `verlauf/qualitaetsserie.json`.

**Betriebsstand 05.10.2026:** Der Nutzer hat beide neuen Videos nach eigener
Aussage manuell auf YouTube UND TikTok hochgeladen. Dies ist als Nutzerangabe
in `verlauf/telegram-sendungen.json` erfasst; Plattform-IDs, Links und
Sichtbarkeit wurden nicht verifiziert. Nicht erneut hochladen.
Die taeglichen GitHub-Zeitplaene fuer Produktion/Telegram und Themen sind aktiv;
die Plattform-Veroeffentlichung bleibt manuell. Die beiden verbesserten Videos
waren kuratierte, manuell gestartete Piloten, kein Nachweis gleichbleibender
Qualitaet des automatischen Tageslaufs. Details siehe Uebergabe.

**Neueste Nutzerrueckmeldung, 05.10.2026:** Beide neuen Videos sind beim
Nutzer angekommen und gefallen ihm deutlich besser als vorher. Das Ziel
bleibt **10/10**, die aktuellen Videos haben keine numerische Nutzernote.
AI Tools Explained: bisher 23 Einstellungen / 12 Motive; fuer kuenftige
vergleichbare Shorts etwa **14-18 unterschiedliche, passende Motive** anstreben.
Business Origin Stories: Das gelieferte Video mit 24 Einstellungen / 14 Motiven
gefaellt; die **neuere Zielvorgabe ist etwa 24 Einstellungen / 18 Motive**.
Die urspruengliche positive Bewertung bleibt erhalten. Nicht einfach mehr
Schnitte/Zooms als neue Motive zaehlen. Verbesserung und Bildstil erhalten,
weitere Qualitaetsarbeit fortsetzen. Wortgetreues Feedback mit Video-SHA256
und wirksame Planungsregeln stehen in `lernen/redaktion.json`, zusaetzliche
Empfangsbestaetigungen in `verlauf/telegram-sendungen.json`.

Die gebaute Technik, alle betroffenen Dateien, reproduzierbare Testbefehle,
Testergebnisse und Grenzen stehen in [UMSETZUNG-UND-TESTS.md](UMSETZUNG-UND-TESTS.md).

Der Nutzer moechte professionelle, abwechslungsreiche Shorts UND Langvideos,
nachweisbares Lernen aus echten Ergebnissen und die Zustellung bestandener
Videos samt Skript und Upload-Texten auf Telegram. Der aktuelle Freigabefilter
verlangt seit der ausdruecklichen Nutzerkorrektur Story und Video jeweils
mindestens 7/10, jede Einzelkategorie mindestens 7/10 (nur die spekulative
Story-Teilbarkeit mindestens 6/10) sowie bestandene
Fakten- und Technikpruefungen. 8/10 bleibt eine Veroeffentlichungsempfehlung,
kein Versandhindernis; 9/10 ist nicht mehr die Mindestnote.

Zusaetzliche ausdrueckliche Vorgaben: Figuren und illustrierte Videogestaltung
sollen eine GTA-artige urbane, gemalte Comic-/Spielplakat-Anmutung haben,
mit eigenstaendigen Charakteren. Keine GTA-Figuren, Logos, Outfits oder
konkreten Spielszenen kopieren. Hintergrundmusik und Geraeusche muessen
inhaltlich und emotional zur Geschichte passen und die Stimme frei lassen.

Die vom Nutzer erneut bestaetigten Referenzen liegen unveraendert in `figuren/`:
Business = Mann mit Hut, grauem Anzug, dunkler Krawatte und goldener Taschenuhr;
AI Tools = schwarzhaariger Mann mit schwarzer Lederjacke und cyan leuchtender Brille.
Die jeweilige Figur erscheint am Anfang UND wiederkehrend im Verlauf des Videos,
in sinnvollen Handlungen. Gesicht und typische Kleidung erhalten; Posen/Schauplaetze
variieren. Historische Handwerker sind Nebenfiguren, keine behaupteten Gruenderportraets.
Lebendige gemalte Spielwelt ist der bevorzugte Look; echte Tool-Beispiele bleiben
gezielte Belege. Die aktuellen Kamerafahrten sind keine volle Figurenanimation.

Neu: `assets/illustrationen/` mit 16 per built-in image_gen erzeugten, visuell
kontrollierten Originalbildern, exakten Promptdateien und SHA256-Katalog.
`fabrik/bibliothek.py` prueft Kanal, ID, Pfad und unveraenderten Dateiinhalt.
Die kuratierten Piloten brauchen damit keine Cloudflare-Bildgenerierung:
das freie Tageskontingent wurde am 05.10.2026 tatsaechlich aufgebraucht.
Keine kostenpflichtige Hochstufung aktiviert. Endgueltige Videos weiterhin
vollstaendig pruefen und vor dem Telegram-Versand manuell visuell ansehen.

Interaktionsaufforderung in jedem Video: explizit **liken, teilen und speichern**.
Shorts: einmal kurz nach der Aufloesung nahe dem Ende. Langvideos: am Anfang
nach Hook/erstem Nutzen und nochmals am Ende nach der Aufloesung.
Knapp und natuerlich formulieren; ein Abo-Aufruf allein reicht nicht.
Es muss ausdruecklich GESPROCHEN werden, etwa "Be sure to like, share and
save this video." (= "Unbedingt liken, teilen und dieses Video speichern.").
Eine Einblendung/Beschreibungszeile allein reicht nicht; nicht optional.

Alte Eintraege mit 8/10 und fruehere Aussagen wie "Pilot noch nicht gestartet"
sind historische Staende. Den neuesten Status in der Uebergabe und auf GitHub
pruefen, bevor ein weiterer Lauf gestartet wird. Keine Tokens ausgeben oder
in Dateien ablegen. Veroeffentlichung auf YouTube/TikTok ist weiterhin manuell.

Die beiden ersten Piloten sind gesperrt (Short: Fakten; Lang: Story 6/10).
Der Nintendo-Short `37331710289` wurde am 05.10.2026 um 17:35 Uhr Berlin
gesendet, danach vom Nutzer ausdruecklich als deutlich schlechter als 5/10
abgelehnt. Die KI-Note 9/10 war unzuverlaessig: zu wenige Motive, rund 27 s
Kerzenhintergrund ohne Hauptbild. KEIN bestaetigter Qualitaetserfolg.
Nutzerfeedback in `lernen/redaktion.json`, Datei per SHA256 erneut gesperrt.
Neu: Gemini-Bildplan mit mehreren Einstellungen PRO Sprechphase, native
Pruefung echter Materialvielfalt und Bildabdeckung, kein Hintergrundersatz.
**Abgeschlossen 05.10.2026, 20:34 Berlin:** neuer AI-Tools-Short (23 Einstellungen,
12 Motive) und neuer Business-Short (24 Einstellungen, 14 Motive) sind gebaut,
anhand echter MP4-Frames kontrolliert und auf Telegram zugestellt: AI message_id
123 um 20:24, Business message_id 130 um 20:33. Beide KI Story/Video 8/10;
Fakten/Technik bestanden, 154 Tests bestanden. Der Nutzer hat anschliessend
Empfang und deutliche Verbesserung bestaetigt; konkrete Folgeziele siehe oben.
Zustellbelege/Hashes in `verlauf/telegram-sendungen.json`; Details in der Uebergabe.
Neue Piloten weiterhin zuerst visuell kontrollieren, danach `github_pilot.py senden`.
Der fehlende Telegram-Hinweis wurde im Pilotablauf korrigiert: Startnachricht
und separater Fehlerjob bei `telegram=true`. Die Uebergabe beschreibt die
konkreten Ergebnisse und die noch offene Abweichung der Langvideo-Themenwahl.
