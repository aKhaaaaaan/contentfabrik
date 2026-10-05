# Einstieg fuer Claude

Bitte zuerst [UEBERGABE-CLAUDE.md](UEBERGABE-CLAUDE.md) und danach
[README.md](README.md), [PROMPTS.md](PROMPTS.md) und [KONZEPT.md](KONZEPT.md)
lesen. Die Uebergabe beschreibt die neuen Aenderungen, den aktuellen
Betriebsstand, Pruefungen und die noch offenen Arbeiten.

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
Fakten/Technik bestanden, 154 Tests bestanden. Nutzerbewertung noch offen.
Zustellbelege/Hashes in `verlauf/telegram-sendungen.json`; Details in der Uebergabe.
Neue Piloten weiterhin zuerst visuell kontrollieren, danach `github_pilot.py senden`.
Der fehlende Telegram-Hinweis wurde im Pilotablauf korrigiert: Startnachricht
und separater Fehlerjob bei `telegram=true`. Die Uebergabe beschreibt die
konkreten Ergebnisse und die noch offene Abweichung der Langvideo-Themenwahl.
