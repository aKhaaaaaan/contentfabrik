# YouTube einrichten – Schritt für Schritt

Stand 02.10.2026. Menünamen können sich bei Google leicht ändern – dann bitte
Bildschirmfoto schicken.

## Teil A – Kanäle anlegen (je Nische ein Kanal, ca. 2 Min. pro Kanal)

1. Am PC **youtube.com** öffnen und mit dem Gmail-Konto anmelden, unter dem
   alle Kanäle laufen sollen.
2. **youtube.com/channel_switcher** öffnen → **„Kanal erstellen"**.
3. Namen eingeben → Häkchen → **„Erstellen"**. Das ist ein Markenkanal: Er
   gehört zum Gmail-Konto, zeigt aber nicht deinen Namen.
4. Für jeden Kanal wiederholen:
   - AI Tools Explained
   - Business Origin Stories
   - Revenge Stories (Arbeitstitel)
   - Psychology Facts (Arbeitstitel)
   Ist ein Name vergeben, eine Variante nehmen und mir mitteilen.

## Teil B – Konto bestätigen (einmal, gilt für alle Kanäle des Kontos)

5. **youtube.com/verify** öffnen → Land → Handynummer → Code eingeben.
   Damit sind lange Videos (über 15 Min.) und eigene Vorschaubilder erlaubt.

## Teil C – Grundeinstellungen je Kanal (YouTube Studio)

6. **studio.youtube.com** öffnen, oben rechts auf das Profilbild → richtigen
   Kanal wählen.
7. Links unten **Einstellungen** → **Kanal** → **Land des Wohnsitzes**:
   dein echtes Land (wichtig für Steuern und Auszahlung).
8. Sonst nichts – Profilbild, Banner, Beschreibung liefert das Tool.

## Teil D – Zugang für das automatische Hochladen (einmal, ca. 10 Min.)

9. **console.cloud.google.com** öffnen (gleiches Gmail-Konto), oben
   **„Projekt auswählen" → „Neues Projekt"** → Name **contentfabrik** →
   Erstellen. (Kostenlos; keine Karte nötig.)
10. Links **APIs & Dienste → Bibliothek** → nacheinander suchen und jeweils
    **„Aktivieren"**:
    - **YouTube Data API v3** (zum Hochladen)
    - **YouTube Analytics API** (für die Zahlen im Dashboard)
11. Links **Google Auth Platform** (bzw. „OAuth-Zustimmungsbildschirm") →
    **Jetzt starten**:
    - App-Name: **Contentfabrik**, Support-E-Mail: deine Gmail-Adresse
    - Zielgruppe: **Extern**
    - Kontaktdaten: deine Gmail-Adresse → Fertigstellen
12. Unter **Zielgruppe → Testnutzer** deine Gmail-Adresse hinzufügen.
13. Links **Clients → Client erstellen** → Anwendungstyp **„Desktop-App"** →
    Name **contentfabrik** → Erstellen → **JSON herunterladen**.
14. Die heruntergeladene Datei **nicht** in den Chat schicken, sondern in den
    Ordner **`C:\Users\saima\Downloads\contentfabrik-geheim\`** legen und mir
    „liegt da" schreiben.

15. **API-Schlüssel für die Trend-Suche** (Vorbild-Analyse: was ist in der
    Nische gerade viral?): **APIs & Dienste → Anmeldedaten → „Anmeldedaten
    erstellen" → „API-Schlüssel"**. Dann **„Schlüssel einschränken"** → unter
    API-Einschränkungen nur **„YouTube Data API v3"** erlauben → Speichern.
    Den Schlüssel **nicht** in den Chat, sondern in PowerShell:
    `setx YOUTUBE_API_KEY "dein-schlüssel"` – und mir „gesetzt" schreiben.

Danach melde ich jeden Kanal einmal am PC an (du wählst im Google-Fenster den
jeweiligen Kanal aus) – ab dann lädt das Tool selbstständig hoch.

## Was vorab zu wissen ist (geprüft)

- **Uploads bleiben zunächst privat**, bis Google unser Projekt geprüft hat
  (kostenlos). Bis dahin: Das Tool lädt privat hoch, du schaltest mit einem
  Tipp in der YouTube-App auf „öffentlich". Den Prüfantrag bereite ich vor
  (dafür baue ich eine kleine Website mit Datenschutzerklärung).
- **Im Testmodus laufen Anmeldungen nach einigen Tagen ab** – das prüfe ich
  beim Einrichten und stelle es so ein, dass das Tool dauerhaft angemeldet
  bleibt.
- Das Tool setzt bei jedem Video die Kennzeichnung **„veränderte oder
  synthetische Inhalte"** (KI-Stimme), wie YouTube es verlangt.
