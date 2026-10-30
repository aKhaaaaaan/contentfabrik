"""Wochenbericht auf Telegram: Was kam beim Publikum an?

Nutzer 30.10.2026 ("alles umsetzen"): Massstab ist das Publikum, nicht die Pruef-KI. erfolg.py holt die echten
Zahlen schon taeglich (YouTube Analytics, TikTok video.list), aber niemand bekam sie zu sehen. Jeden Montag
(Berlin) einmal: Lieferquote, Aufrufe, Zuschauerbindung nach den ersten Sekunden, bestes/schwaechstes Video.
Nur gemessene Werte; fehlt etwas, steht "noch keine Daten" da.
"""
import datetime
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

KANAELE = {'business-origin-stories': 'Business Origin Stories', 'ai-tools-explained': 'AI Tools Explained'}
MARKE = Path('erfolg/.letzter_wochenbericht')
TAGE = 7
FRUEH = 0.17  # Anteil der Videolaenge, an dem die Bindung abgelesen wird (~7 s bei 40 s)


def _laden(pfad, leer):
    try:
        return json.loads(Path(pfad).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return leer


def lieferquote(name, heute, tage=TAGE):
    """(Tage mit zugestelltem Video, Tage) - je Tag zaehlt hoechstens ein Video."""
    von = heute - datetime.timedelta(days=tage)
    daten = {str(x.get('datum_utc', ''))[:10] for x in _laden('verlauf/telegram-videos.json', [])
             if x.get('kanal') == name}
    return sum(1 for d in daten if von.isoformat() < d <= heute.isoformat()), tage


def frueh_bindung(kurve, stelle=FRUEH):
    """Anteil der Zuschauer bei `stelle` der Laenge aus [[anteil, verhaeltnis], ...] (YouTube audienceWatchRatio)."""
    punkte = [p for p in kurve or [] if isinstance(p, (list, tuple)) and len(p) == 2]
    if not punkte:
        return None
    return min(punkte, key=lambda p: abs(p[0] - stelle))[1]


def _neu(videos, heute, tage, reife=2):
    """Videos der letzten `tage`, aber erst ab `reife` Tagen alt - ein Video von gestern hat 4 Aufrufe und waere
    sonst immer das "schwaechste"."""
    von = (heute - datetime.timedelta(days=tage)).isoformat()
    bis = (heute - datetime.timedelta(days=reife)).isoformat()
    return [v for v in videos if isinstance(v, dict) and von < str(v.get('veroeffentlicht', '')) <= bis
            and isinstance(v.get('aufrufe'), int)]


def _titel(v):
    return re.sub(r'\s*#\w+', '', str(v.get('titel', ''))).strip()[:50]


def _zeile_bestes(vs):
    if len(vs) < 2:
        return []
    vs = sorted(vs, key=lambda v: v['aufrufe'])
    return [f"   Bestes: {vs[-1]['aufrufe']} - {_titel(vs[-1])}",
            f"   Schwaechstes: {vs[0]['aufrufe']} - {_titel(vs[0])}"]


def kanal_text(slug, heute):
    name = KANAELE[slug]
    d = _laden(f'erfolg/{slug}.json', {})
    geliefert, tage = lieferquote(name, heute)
    zeilen = [f'📺 {name}', f'Videos zugestellt: an {geliefert} von {tage} Tagen']
    yt = _neu(list((d.get('videos') or {}).values()), heute, 14)
    if yt:
        anteil = [v['anteil_prozent'] for v in yt if isinstance(v.get('anteil_prozent'), (int, float))
                  and 0 < v['anteil_prozent'] <= 100]
        frueh = [f for f in (frueh_bindung(v.get('kurve')) for v in yt) if f]
        # 30.10.2026: engagedViews/views = wer im Shorts-Feed weiterschaut statt wegzuwischen (Business 17 %)
        bleiben = [v['engaged'] / v['aufrufe'] for v in yt if isinstance(v.get('engaged'), int) and v['aufrufe'] >= 10]
        zeilen.append(f'YouTube (14 Tage, {len(yt)} Videos): Median {statistics.median(v["aufrufe"] for v in yt):.0f} '
                      'Aufrufe' + (f', im Schnitt {statistics.mean(anteil):.0f} % angesehen' if anteil else ''))
        if bleiben:
            zeilen.append(f'   Im Feed weitergeschaut statt weggewischt: {statistics.mean(bleiben) * 100:.0f} %')
        if frueh:
            zeilen.append(f'   Nach den ersten Sekunden noch dabei: {statistics.mean(frueh) * 100:.0f} %'
                          + (' - der Einstieg verliert zu viele' if statistics.mean(frueh) < .75 else ''))
        zeilen += _zeile_bestes(yt)
    else:
        zeilen.append('YouTube: noch keine Daten')
    tt = d.get('tiktok') or {}
    tt = _neu(list(tt.values()) if isinstance(tt, dict) else tt, heute, 14)
    if tt:
        zeilen.append(f'TikTok (14 Tage, {len(tt)} Videos): Median {statistics.median(v["aufrufe"] for v in tt):.0f} '
                      f'Aufrufe, {sum(v.get("likes") or 0 for v in tt)} Likes, '
                      f'{sum(v.get("teilungen") or 0 for v in tt)} Teilungen')
        zeilen += _zeile_bestes(tt)
    else:
        zeilen.append('TikTok: noch keine Daten')
    return '\n'.join(zeilen)


def text(heute):
    return '📊 Wochenbericht - was beim Publikum ankam\n\n' + '\n\n'.join(kanal_text(k, heute) for k in KANAELE)


def faellig(heute, marke=MARKE):
    """Montags einmal; verpasster Montag wird am naechsten Tag nachgeholt (Marke aelter als 6 Tage)."""
    try:
        letzter = datetime.date.fromisoformat(marke.read_text(encoding='utf-8').strip())
    except (OSError, ValueError):
        letzter = None
    return (letzter is None and heute.weekday() == 0) or (letzter is not None and (heute - letzter).days >= 7)


if __name__ == '__main__':
    from zoneinfo import ZoneInfo
    heute = datetime.datetime.now(ZoneInfo('Europe/Berlin')).date()
    if '--jetzt' not in sys.argv and not faellig(heute):
        print('Wochenbericht nicht faellig')
        sys.exit(0)
    nachricht = text(heute)
    print(nachricht)
    if '--nur-zeigen' in sys.argv:
        sys.exit(0)
    import statusmeldung
    statusmeldung.senden(nachricht)
    MARKE.parent.mkdir(exist_ok=True)
    MARKE.write_text(heute.isoformat(), encoding='utf-8')
