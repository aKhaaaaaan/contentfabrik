# TikTok-App „Contentfabrik" – Antrag (Stand 03.10.2026)

## Pruefhindernis festgestellt am 05.10.2026

Die offizielle Direct-Post-Richtlinie verlangt einen Anwendungsfall fuer ein
breites Publikum und schliesst reine private Werkzeuge zum Hochladen auf
eigene/Team-Konten ausdruecklich aus. Der unten beschriebene private
Anwendungsfall passt daher nicht zu diesen Audit-Anforderungen. Die
beschraenkte Nutzung ungepruefter Clients ist keine Zusage fuer eine spaetere
Freischaltung. Bis zur Klaerung bleibt der aktive Ablauf beim manuellen
Upload; eine Pruefentscheidung oder neue Antragseinreichung wird hier nicht
vorweggenommen.

Quelle: [TikTok – Direct Post, Intended Use](https://developers.tiktok.com/docs/en/content-sharing-guidelines),
abgerufen am 05.10.2026. Der folgende Text bleibt als damaliger Entwurf erhalten.

App-ID (Entwurf): 7692400168096794631 · Konto: [privates Google-Konto] · Typ: Individual

## Bereits eingetragen
- Symbol: website/icon.png (1024×1024) · Kategorie: Education
- Beschreibung (120 Zeichen): „Private tool that creates short educational videos and posts them to the owner's own TikTok account after review."
- Terms: https://contentfabrik.pages.dev/terms · Privacy: https://contentfabrik.pages.dev/privacy
- Plattform: Web · Web-URL: https://contentfabrik.pages.dev/
- URL-Nachweis: URL-Präfix https://contentfabrik.pages.dev/ – **bestätigt** (Prüfdatei liegt auf der Website)

## Noch offen (TikTok speichert erst, wenn alles da ist)
1. **Nutzungsbeschreibung** (Text unten)
2. **Vorführvideo** des kompletten Ablaufs, aufgenommen in der TikTok-Sandbox:
   Anmeldung mit TikTok (Login Kit) → Video wird über die Content Posting API hochgeladen → Ergebnis im TikTok-Konto
3. Produkte: Login Kit, Content Posting API · Scopes: user.info.basic, video.upload, video.publish

## Nutzungsbeschreibung (für das Feld „App review“)
Contentfabrik is a private tool used only by its owner. It produces short educational videos (facts about new
open-source AI models and the history of well-known companies) from public sources such as Wikipedia, GitHub and
Hugging Face. Every script is fact-checked and every video is reviewed by the owner before publishing. We use Login
Kit so the owner can connect their own TikTok account once, and the Content Posting API (video.upload /
video.publish) to upload the finished, approved video to that account with title, description, AI-content label and
privacy setting chosen by the owner. We do not access other users' accounts or data, we do not read or store any
viewer data, and we do not post without the owner's approval.

## Wichtig (geprüft in der TikTok-Doku)
„All content posted by unaudited clients will be restricted to private viewing mode." – erst nach der Prüfung
kann das Tool öffentlich posten.
