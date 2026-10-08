# Neuen Kanal anlegen (Stand 08.10.2026)

Ein neuer Kanal erbt alles Bewaehrte automatisch aus `fabrik/kanalstandard.py`:
Gemini-Stimme **Orus**, **Tempo 1.08**, warmer filmischer Erzaehlstil, ~2.1 Woerter/s,
Laenge 62-90 s, **keine Stockclips** (alles gemalt), YouTube-Kategorie 27 (Bildung).
Werte im Kanalprofil haben immer Vorrang; `erzaehlstimme` wird feldweise gemischt
(z. B. nur `stil` aendern, Tempo bleibt 1.08).

## Schritte

1. `kanaele/<slug>.json` anlegen, Minimalbeispiel:
   ```json
   {
     "name": "Sports Legends",
     "format": "geschichte",
     "telegram_kuerzel": ["sport", "legende"],
     "beschreibung_kurz": "how famous athletes and clubs rose",
     "erzaehlstimme": {"stil": "deep cinematic trailer voice, proud and emotional"}
   }
   ```
   `format`: `geschichte` (Story) oder `erklaerung` (Tool/Anleitung). Weitere Felder wie in
   den bestehenden Profilen (Themenquellen, Hashtags) nach Bedarf uebernehmen.
   Dateien, die mit `_` beginnen, gelten nicht als Kanal (Vorlagen).
2. Wiederkehrende Figur als Referenzbild: `figuren/<slug>.jpg` (eigene, originale Figur).
3. Telegram: sofort ansprechbar ueber die `telegram_kuerzel` (z. B. `Sport: Wie Nike ...`),
   die automatische Kanalzuordnung nutzt `beschreibung_kurz`.
4. Tageslauf: in `.github/workflows/video.yml` die Matrix um den Slug ergaenzen und im
   Cloudflare-Worker (`cloudflare/zeitplan-worker.js`, `KANAELE`) den Start-Befehl eintragen,
   danach Worker neu deployen.
5. YouTube-Upload (spaeter): eigenes OAuth-Token `token-<kanal_id>.json` im Geheim-Ordner;
   Kategorie ueber `youtube_kategorie` (28 = Wissenschaft & Technik).

## Pruefen

`python -m unittest discover -s pruefungen` - `test_kanalstandard.py` legt testweise einen
Kanal "Sports Legends" an und prueft Stimme, Tempo, Stockclips, Wortrate, Kategorie und Telegram.
