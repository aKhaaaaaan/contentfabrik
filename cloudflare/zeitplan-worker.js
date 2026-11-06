// Zusaetzlicher Zeitplan fuer die Contentfabrik (Cloudflare Workers, Cron Triggers).
//
// GEMESSEN 04./05.10.2026: GitHub startete die zeitgesteuerten Laeufe 7 Stunden zu spaet
// bzw. gar nicht ("schedule events may be delayed during periods of high load").
// Dieser Worker stoesst den Lauf ueber die offizielle GitHub-Schnittstelle
// an (workflow_dispatch). kanal=alle -> die Vorpruefung nimmt nur Kanaele ohne freigegebenes Video.
//
// Einrichtung (einmalig, Cloudflare-Dashboard -> Workers & Pages -> Create -> Worker):
//   1. diesen Code einfuegen
//   2. Settings -> Variables and Secrets -> Secret GH_TOKEN = GitHub-Fine-grained-Token
//      (nur Repository aKhaaaaaan/contentfabrik, nur "Actions: Read and write")
//   3. Settings -> Triggers -> Cron Triggers (UTC): 23 8,13 * * *, 41 10,15 * * *
//      und fuer die Themen-Abholung: */5 * * * *
//   Alternativ: npx wrangler deploy --config cloudflare/wrangler.json --keep-vars
//
// Befehls-Bot (08.10.2026): zweiter Telegram-Bot nur fuer Start/Status.
//   4. @BotFather -> /newbot -> Token als Secret TG_BEFEHL_TOKEN eintragen
//   5. <worker-url>/einrichten einmal im Browser oeffnen (setzt den Webhook)
//   6. dem neuen Bot „Hallo" schreiben -> er nennt die Chat-ID -> Variable TG_CHAT_ID
//   Befehle: Start | Start Business | Start KI | Status (Gesamtfortschritt in %) | Abholen

const REPO = 'aKhaaaaaan/contentfabrik';
const VERSION = '2026-10-23.1';
// Zusammengefasste Stunden sparen Trigger: Workers Free hat fuenf pro Konto.
const VIDEO_CRONS = new Set(['23 8,13 * * *', '41 10,15 * * *',
  '23 8 * * *', '41 10 * * *', '23 13 * * *', '41 15 * * *']);

async function starte(env, workflow, inputs) {
  if (!env.GH_TOKEN) throw new Error('GH_TOKEN fehlt');
  const headers = {
    Authorization: `Bearer ${env.GH_TOKEN}`,
    Accept: 'application/vnd.github+json',
    'User-Agent': 'contentfabrik-zeitplan',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type': 'application/json',
  };
  // Aktiven/noch wartenden Lauf nicht erneut einreihen. Kanalbudget bleibt
  // zusaetzlich die Sperre gegen spaet eintreffende GitHub-Cron-Doppelstarts.
  const status = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/runs?per_page=10`,
    { headers });
  if (!status.ok) throw new Error(`${workflow}: Statuspruefung fehlgeschlagen (HTTP ${status.status})`);
  const daten = await status.json();
  if (!Array.isArray(daten.workflow_runs)) throw new Error(`${workflow}: Statusantwort ungueltig`);
  // GEMESSEN 21.10.2026: themen.yml-Lauf 39462950781 (20.10. 17:05 UTC) hing 16 h in "queued" ohne Runner -
  // jeder 5-Min.-Start meldete "bereits aktiv", Telegram-Klicks (TikTok-Knopf) wurden nicht mehr abgeholt.
  // Ein Lauf, der laenger als 60 Min. wartet, gilt als haengend und blockiert nicht mehr.
  const wartet = (r) => ['queued', 'pending', 'waiting', 'requested'].includes(r.status);
  const haengt = (r) => wartet(r) && Date.now() - Date.parse(r.created_at) > 60 * 60 * 1000;
  if (daten.workflow_runs.some(r => (r.status === 'in_progress' || wartet(r)) && !haengt(r))) {
    return `${workflow}: bereits aktiv oder wartet; kein Doppelstart`;
  }
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ref: 'main', inputs }),
  });
  if (!r.ok) throw new Error(`${workflow}: GitHub-Start fehlgeschlagen (HTTP ${r.status})`);
  return `${workflow}: ${r.status}`;
}

// ---- Befehls-Bot (Telegram) ----------------------------------------------------
// GEMELDET 08.10.2026: „Kann ich vom Telegram aus Start tippen und die Pipeline startet?"
// Der Videobot holt Nachrichten nur alle 4 h ab (getUpdates); ein Webhook schliesst
// getUpdates aus. Darum ein ZWEITER Bot nur fuer Befehle (Secret TG_BEFEHL_TOKEN).
// Nur der eigene Chat (TG_CHAT_ID) darf starten; hoechstens START_MAX manuelle Laeufe/Tag.
// 21.10.2026: Nutzer will weitere Videos, solange das Gratis-Kontingent reicht (Vorpruefung prueft es).
// Vorher zaehlten die vier Zeitplanstarts (ebenfalls workflow_dispatch) mit - am 20.10. war 6 schon nach
// zwei Handstarts erreicht. Jetzt nur Handstarts, Grenze 12 nur gegen versehentliches Dauerstarten.
const START_MAX = 12;
const zeitplanStart = (iso) => {
  const d = new Date(iso);
  const min = d.getUTCHours() * 60 + d.getUTCMinutes();
  return [...VIDEO_CRONS].some((c) => {
    const [m, hs] = c.split(' ');
    return hs.split(',').some((h) => min - (Number(h) * 60 + Number(m)) >= 0 && min - (Number(h) * 60 + Number(m)) <= 10);
  });
};
const KANAELE = { business: 'business-origin-stories', ki: 'ai-tools-explained', ai: 'ai-tools-explained' };
// Nutzer 05.11.2026: "Befehlsliste ausbauen, Befehle fuer Themen, bei einem unbekannten Wort die Liste zeigen,
// fehlende Befehle aufnehmen, schoener machen". Klartext (kein parse_mode) - Sonderzeichen brechen nichts.
const HILFE = [
  '📋 Befehle – Contentfabrik Steuerung',
  '',
  '▶️ Videos starten',
  '• Start – beide Kanäle',
  '• Start Business – nur Business Origin Stories',
  '• Start KI – nur AI Tools Explained',
  '• Start KI bezahlt / Start Business bezahlt – auch wenn das Gratis-Kontingent leer ist',
  '',
  '🎬 Langvideo',
  '• Langvideo Business / Langvideo KI – Langvideo jetzt statt am Plantag (Business Fr, KI Sa)',
  '  (nur wenn in den letzten 6 Tagen keins geliefert wurde)',
  '',
  '🗂 Themen',
  '• Themen – was als Nächstes drankommt (beide Kanäle)',
  '• Themen Business / Themen KI – nur ein Kanal',
  '',
  '📊 Überblick',
  '• Status – was gerade läuft, in Prozent',
  '• Abholen – Feedback und Themen aus dem Videobot sofort verarbeiten',
  '• Hilfe – diese Liste',
  '',
  '💬 Im Videobot (nicht hier)',
  '• Business: Wie LEGO entstand – neues Thema',
  '• KI: Claude Code Schritt für Schritt – neues Thema',
  '• Business: + je Zeile eine Idee – bis zu 25 Themen auf einmal',
  '• Business: <YouTube-/TikTok-Link> – Thema aus einem Video, neu recherchiert',
  '• Skript Business: <Thema> + darunter dein Text – eigenes Skript',
  '• Feedback: … oder auf ein Video antworten – Rückmeldung',
  '• Unter jedem Video: ✅/❌, Note oder „TikTok-Entwurf hochladen“ antippen',
].join('\n');

// GEMESSEN 08.10.2026: Am Handy eingefuegter Token -> Telegram 'Not Found' (ungueltig).
// Leerzeichen/Zeilenumbrueche und ein mitkopiertes 'bot' davor entfernen.
const tgToken = (env) => String(env.TG_BEFEHL_TOKEN || '').trim().replace(/^bot/i, '').replace(/\s+/g, '');

async function geheimnis(env) {
  // Webhook-Schutz ohne weiteres Secret: aus dem Bot-Token abgeleitet (A-Z, a-z, 0-9 erlaubt).
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('cf-befehl:' + tgToken(env)));
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}

async function antworten(env, chat, text) {
  return fetch(`https://api.telegram.org/bot${tgToken(env)}/sendMessage`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    // Ohne Vorschau: sonst haengt Telegram unter jede Statusmeldung eine grosse GitHub-Karte.
    body: JSON.stringify({ chat_id: chat, text, link_preview_options: { is_disabled: true } }),
  });
}

function ghKopf(env) {
  return { Authorization: `Bearer ${env.GH_TOKEN}`, Accept: 'application/vnd.github+json',
    'User-Agent': 'contentfabrik-zeitplan', 'X-GitHub-Api-Version': '2022-11-28' };
}

async function laeufe(env, zusatz = '', workflow = 'video.yml', anzahl = 20) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/runs?per_page=${anzahl}${zusatz}`,
    { headers: ghKopf(env) });
  if (!r.ok) throw new Error(`Status HTTP ${r.status}`);
  return (await r.json()).workflow_runs || [];
}

const berlin = (iso) => new Date(iso).toLocaleTimeString('de-DE',
  { timeZone: 'Europe/Berlin', hour: '2-digit', minute: '2-digit' });

// GEMELDET 08.10.2026: „Ein Status-Wort, zum Beispiel noch 60 % bei Bildgenerierung."
// Grundversion: aktueller GitHub-Schritt + Zeit. Die Produktion hat hoechstens 30 Minuten
// (BUDGET_S), daraus eine ehrliche Schaetzung - keine gemessene Bildzahl.
const PRODUKTION_MIN = 45;

async function ergebnis(lauf, kanal) {
  try {
    const r = await fetch(`https://raw.githubusercontent.com/${REPO}/main/verlauf/messungen/${kanal}.json`);
    const eintrag = r.ok ? ((await r.json()) || []).find(e => String(e.id) === String(lauf.id)) : null;
    if (!eintrag) return 'beendet, Ergebnis meldet der Videobot';
    return eintrag.status === 'gesendet' ? '✅ Video geliefert' : '❌ kein Video - Grund meldet der Videobot';
  } catch (e) {
    return 'beendet, Ergebnis meldet der Videobot';
  }
}

export async function fortschritt(env, lauf) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/runs/${lauf.id}/jobs`, { headers: ghKopf(env) });
  const jobs = r.ok ? ((await r.json()).jobs || []) : [];
  // GEMELDET 08.10.2026: „Gesamte Pipeline in Prozent." Je Kanal: Einrichtung 0-10 %,
  // Produktion 10-90 % (nach Zeit, max. 30 Min), Sichern/Versand 90-100 %; Kanaele zu gleichen Teilen.
  const kanaljobs = jobs.filter(j => j.name.startsWith('video ('));
  const job = jobs.find(j => j.status === 'in_progress');
  const name = j => j.name.replace(/^video \((.*)\)$/, '$1');
  // GEMELDET 17.10.2026 (Screenshot 15:47): "Gesamt: 0 %" ohne Angabe, welcher Lauf das ist.
  if (!job) return `Shorts-Tageslauf: wartet, bis der laufende Lauf fertig ist (seit ${berlin(lauf.created_at)}). `
    + `Sind heute schon alle Shorts geliefert, prueft er nur kurz und baut nichts.\n${lauf.html_url}`;
  const schritte = job.steps || [];
  const schritt = schritte.find(s => s.status === 'in_progress');
  const produktion = schritte.find(s => s.name.startsWith('Erzeugen'));
  let anteil = 0.05, zeile = '', echt = false;
  if (produktion && produktion.status === 'completed') anteil = 0.95;
  else if (schritt && schritt.name.startsWith('Erzeugen')) {
    const g = await gemeldet(env, lauf);
    echt = Boolean(g && g.kanal === name(job));
    const minuten = Math.max(0, (Date.now() - new Date(schritt.started_at)) / 60000);
    anteil = echt ? g.prozent / 100 : 0.1 + 0.8 * Math.min(1, minuten / PRODUKTION_MIN);
    zeile = echt ? `\n${g.text}` : `\nSkript, Stimme, Bilder, Pruefung laufen seit ${Math.round(minuten)} Min`;
  }
  const fertig = kanaljobs.filter(j => j.status === 'completed');
  const gesamt = kanaljobs.length || 1;
  const prozent = Math.min(99, Math.round((fertig.length + anteil) / gesamt * 100));
  let text = `Shorts-Tageslauf - Gesamt: ${echt ? '' : 'ca. '}${prozent} %${echt ? '' : ' (geschaetzt)'}\nJetzt: ${name(job)} - ${schritt ? schritt.name : 'Vorbereitung'}` + zeile;
  // GEMELDET 15.10.2026: "Schon fertig" hiess auch "ohne Video" (Job-success = Lauf beendet).
  // Das echte Ergebnis steht in verlauf/messungen/<kanal>.json (bericht.status 'gesendet').
  for (const j of fertig) text += `\nFertig: ${name(j)} (${await ergebnis(lauf, name(j))})`;
  return text + `\n${lauf.html_url}`;
}

// GEMELDET 08.10.2026 (Screenshot 21:09): Status zeigte nur Tageslaeufe - der laufende
// Langvideo-Pilot (pilot.yml) war unsichtbar. Jetzt beide Ablaeufe, mit Art und Datum.
const PILOT_MIN = { lang: 150, short: 45, woche: 200 };  // geschaetzt; woche = Budget lauf.BUDGET_LANG_S
// GEMELDET 17.10.2026 (Screenshot 14:39): das woechentliche Langvideo (langvideo.yml) lief, Status sagte
// "Gerade laeuft nichts". Es zaehlt jetzt mit.
const art = r => r.path && r.path.includes('langvideo.yml') ? 'Langvideo'
  : r.path && r.path.includes('pilot.yml')
    ? (/\/ lang \//.test(r.display_title || '') ? 'Langvideo-Probe' : 'Short-Probe') : 'Shorts-Tageslauf';
const tag = (iso) => new Date(iso).toLocaleDateString('de-DE', { timeZone: 'Europe/Berlin', day: '2-digit', month: '2-digit' });

// Nutzer 25.10.2026 ("hat es von vorne wieder anfangen", "Prozentual find ich schon besser"): die Uhr-Schaetzung
// liess einen fortgesetzten Bau wie einen Neustart aussehen. lauf.py meldet den echten Stand (fabrik/fortschritt.py);
// ohne frische Meldung bleibt die Schaetzung. Schluessel aus dem Videobot-Token, den beide Seiten schon haben.
const FORTSCHRITT_FRISCH_MS = 20 * 60000;
async function fortschrittSchluessel(env) {
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('cf-fortschritt:' + vbToken(env)));
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}
async function fortschrittEingang(request, env) {
  if (!env.ZUSTAND || !vbToken(env) || request.headers.get('X-CF-Schluessel') !== await fortschrittSchluessel(env)) {
    return new Response('verboten', { status: 403 });
  }
  const d = await request.json().catch(() => null) || {};
  const lauf = String(d.lauf || ''), kanal = String(d.kanal || ''), prozent = d.prozent;
  if (!/^\d{1,20}$/.test(lauf) || !/^[a-z0-9-]{1,60}$/.test(kanal) || !Number.isInteger(prozent)
      || prozent < 0 || prozent > 99) return new Response('ungueltig', { status: 400 });
  const text = String(d.text || '').replace(/[\u0000-\u001f<>]/g, ' ').slice(0, 160);
  await env.ZUSTAND.put(`fortschritt:${lauf}`, JSON.stringify({ kanal, prozent, text, zeit: Date.now() }),
    { expirationTtl: 8 * 3600 });
  return new Response('ok');
}
async function gemeldet(env, lauf) {
  if (!env.ZUSTAND) return null;
  try {
    const d = JSON.parse(await env.ZUSTAND.get(`fortschritt:${lauf.id}`) || 'null');
    return d && Date.now() - d.zeit < FORTSCHRITT_FRISCH_MS ? d : null;
  } catch (e) {
    return null;
  }
}

export async function pilotFortschritt(env, lauf) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/runs/${lauf.id}/jobs`, { headers: ghKopf(env) });
  const job = (r.ok ? ((await r.json()).jobs || []) : []).find(j => j.status === 'in_progress');
  const titel = art(lauf);
  if (!job) return `${titel}: wartet auf einen freien Rechner (seit ${berlin(lauf.created_at)}).\n${lauf.html_url}`;
  const schritt = (job.steps || []).find(x => x.status === 'in_progress');
  const istBau = x => x.name.startsWith('Video bauen') || x.name.startsWith('Erzeugen');
  const bau = (job.steps || []).find(istBau);
  const ziel = PILOT_MIN[titel === 'Langvideo' ? 'woche' : titel === 'Langvideo-Probe' ? 'lang' : 'short'];
  let anteil = 0.05, zeile = '';
  if (bau && bau.status === 'completed') anteil = 0.95;
  else if (schritt && istBau(schritt)) {
    const g = await gemeldet(env, lauf);
    if (g) return `${titel}: ${g.prozent} %\nJetzt: ${g.text}\n${lauf.html_url}`;
    const minuten = Math.max(0, (Date.now() - new Date(schritt.started_at)) / 60000);
    anteil = 0.1 + 0.8 * Math.min(1, minuten / ziel);
    zeile = `\nSkript, Stimme, Bilder, Pruefung laufen seit ${Math.round(minuten)} Min (erwartet ca. ${ziel} Min)`;
  }
  return `${titel}: ca. ${Math.min(99, Math.round(anteil * 100))} % (geschaetzt)\n`
    + `Jetzt: ${schritt ? schritt.name : 'Vorbereitung'}${zeile}\n${lauf.html_url}`;
}

// Nutzer 29.10.2026: "Welche Themen stehen an? Auch bei Telegram, damit ich weiss, was in der Pipeline steht."
// Wie lauf.py: fertig geprueftes Vorrat-Skript zuerst, sonst waehlt trendcheck aus Warteschlange und Trends.
const KANAL_NAME = { 'ai-tools-explained': 'KI', 'business-origin-stories': 'Business' };

async function roh(pfad) {
  const r = await fetch(`https://raw.githubusercontent.com/${REPO}/main/${pfad}`);
  return r.ok ? r.json() : null;
}

const WOCHENTAG = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];

function tagText(iso) {
  if (!iso) return '';
  const d = new Date(iso + 'T12:00:00Z');
  return `${WOCHENTAG[d.getUTCDay()]} ${iso.slice(8, 10)}.${iso.slice(5, 7)}.`;
}

// Nutzer 06.11.2026: "Themen-Befehl praeziser, zum Beispiel Shorts und Long Themen" - je Kanal zwei Bloecke.
// Langvideo: verlauf/themenplan/lang-<kanal>.json (langvideo.py vorschau, taeglich und nach jedem Langvideo-Lauf).
export function langBlock(lang, heute) {
  if (!lang || !lang.termin) return '🎞 Langvideo: kein Termin geplant (formate/<kanal>.json lang_tage)';
  const [von, bis] = lang.laenge_s || [];
  const dauer = von && bis ? ` (${Math.round(von / 60)}–${Math.round(bis / 60)} Min.)` : '';
  const termin = lang.termin === heute ? `heute, ${tagText(lang.termin)}` : tagText(lang.termin);
  const zeilen = [`🎞 Langvideo${dauer}`, `Termin: ${termin} ab 13:07` + (lang.ersatz ? ` · Ersatz ${tagText(lang.ersatz)}` : '')];
  if (lang.fest) zeilen.push(`Thema: ${lang.fest} (${lang.fest_grund || 'fest'})`);
  else if ((lang.kandidaten || []).length) {
    zeilen.push('Kandidaten (aus den Shorts der letzten Tage; der Trend-Check wählt am Termin):');
    zeilen.push(...lang.kandidaten.map((t, i) => `${i + 1}. ${t}`));
    if (!lang.quellen_geprueft) zeilen.push('Quellen prüft der Lauf selbst.');
  } else zeilen.push('Thema: freie Wahl (kein passender Short der letzten Tage)');
  if (lang.erstellt && lang.erstellt !== heute) zeilen.push(`(Stand ${tagText(lang.erstellt)})`);
  return zeilen.join('\n');
}

export function shortBlock(fertig, plan, offen, trend, heute) {
  const zeilen = ['📱 Shorts (35–45 s, täglich)'];
  if (fertig.length) zeilen.push(`Skript fertig (kommt zuerst): ${fertig.join(', ')}`);
  if (trend && trend.thema) zeilen.push(`Heute: ${trend.thema}`);
  const tage = plan && plan.erstellt ? (Date.parse(heute) - Date.parse(plan.erstellt)) / 86400000 : 99;
  const reihe = tage >= 0 && tage < 3 ? (plan.reihenfolge || []).filter(t => !trend || t !== trend.thema) : [];
  if (reihe.length) zeilen.push(`Redaktionsplan (Stand ${tagText(plan.erstellt)}): ${reihe.join(' · ')}`);
  zeilen.push(offen.length ? 'Warteschlange (deine Themen):\n' + offen.map((t, i) => `${i + 1}. ${t}`).join('\n')
    : 'Warteschlange (deine Themen): leer');
  return zeilen.join('\n');
}

export async function themenUebersicht(env, nur = '') {
  const heute = new Date().toISOString().slice(0, 10);
  const geladen = await roh('themen/warteschlange.json').catch(() => null);
  const schlange = Array.isArray(geladen) ? geladen : [];
  const teile = [];
  for (const [kanal, name] of Object.entries(KANAL_NAME)) {
    if (nur && nur !== kanal) continue;
    const vorrat = await fetch(`https://api.github.com/repos/${REPO}/contents/vorrat/${kanal}`, { headers: ghKopf(env) })
      .then(r => r.ok ? r.json() : []).catch(() => []);
    // Ein Langvideo-Skript im Vorrat steht im Langvideo-Block (vorschau.fest), nicht bei den Shorts.
    const lang = await roh(`verlauf/themenplan/lang-${kanal}.json`).catch(() => null);
    // GEMESSEN 06.11.2026: der Dateiname ("codex-16f6a9ce...") ist kein Thema - Inhalt lesen (meist 0-3 Dateien).
    const dateien = (Array.isArray(vorrat) ? vorrat : []).filter(f => f.name.endsWith('.json')).slice(0, 6);
    const fertig = (await Promise.all(dateien.map(f => roh(`vorrat/${kanal}/${f.name}`).catch(() => null))))
      .filter(e => e && e.skript && e.skript.videoformat !== 'lang')
      .map(e => e.thema_eingabe || e.skript.thema).filter(Boolean);
    const offen = schlange.filter(e => e.kanal === kanal && (e.status || 'bereit') === 'bereit').map(e => e.thema);
    const trend = await roh(`verlauf/trendcheck/${kanal}-${heute}.json`).catch(() => null);
    const plan = await roh(`verlauf/themenplan/${kanal}.json`).catch(() => null);
    teile.push(`━━ ${name} ━━\n` + shortBlock(fertig, plan, offen, trend, heute) + '\n\n' + langBlock(lang, heute));
  }
  return '🗂 Themen in der Pipeline\n\n' + teile.join('\n\n') +
    '\n\nNeue Themen im Videobot mit „Business: ..." oder „KI: ..." schicken.';
}

export async function befehl(env, text) {
  // GEMELDET 24.10.2026: "Status?" bekam die Befehlsliste - Satzzeichen am Ende zaehlen nicht.
  // "/" bleibt: "/start" sendet Telegram beim ersten Oeffnen, das darf nichts starten.
  const t = String(text || '').toLowerCase().replace(/[\s?!.,;:]+$/, '').replace(/\s+/g, ' ').trim();
  if (t === 'status') {
    const [video, pilot, woche] = await Promise.all([laeufe(env, '', 'video.yml', 5),
      laeufe(env, '', 'pilot.yml', 5).catch(() => []), laeufe(env, '', 'langvideo.yml', 3).catch(() => [])]);
    const rs = [...video, ...pilot, ...woche].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
    if (!rs.length) return 'Noch keine Videolaeufe.';
    const aktiv = rs.filter(r => r.status !== 'completed');
    if (aktiv.length) {
      const teile = await Promise.all(aktiv.map(r => art(r) === 'Shorts-Tageslauf' ? fortschritt(env, r) : pilotFortschritt(env, r)));
      return teile.join('\n\n');
    }
    return 'Gerade laeuft nichts. Letzte Laeufe:\n' + rs.slice(0, 4).map(r => `${tag(r.created_at)} ${berlin(r.created_at)} - ${art(r)} - ${
      r.conclusion === 'success' ? 'beendet' : r.conclusion === 'cancelled' ? 'abgebrochen' : 'Fehler'}\n${r.html_url}`)
      .join('\n') + '\n\n„Beendet" heisst nicht automatisch Video - das Ergebnis meldet der Videobot.';
  }
  if (t === 'hilfe' || t === 'help' || t === 'befehle' || t === '/start' || t === '/help') return HILFE;
  const th = t.match(/^(?:themen|thema)(?:\s+(business|ki|ai))?$/);
  if (th) return themenUebersicht(env, th[1] ? KANAELE[th[1]] : '');
  // Themen gehoeren in den Videobot (themen.py liest nur dort) - nicht still als Unbekannt abtun.
  if (/^(business|ki|ai|skript\s+\w+)\s*:/.test(t)) {
    return 'Themen und Skripte bitte im Videobot schicken - dieser Bot startet nur und zeigt den Stand.\n\n' + HILFE;
  }
  // Nutzer 05.11.2026: "Longvideo-Befehle hab ich in der Liste nicht gefunden". langvideo.yml mit gesetztem
  // Kanal = Handstart ohne Wochentagspruefung; langvideo.faellig() verhindert ein zweites Langvideo im Abstand.
  const lv = t.match(/^(?:start\s+)?(?:langvideo|longvideo|lang)\s+(business|ki|ai)$/);
  if (lv) {
    const e = await starte(env, 'langvideo.yml', { kanal: KANAELE[lv[1]], thema: '' });
    if (e.includes('bereits aktiv')) return 'Es laeuft gerade schon ein Langvideo - kein Doppelstart. Schreib „Status".';
    return `Langvideo gestartet (${KANAELE[lv[1]]}). Dauert ca. 60-120 Minuten; Ergebnis ueber den Videobot.\n` +
      'Wurde in den letzten 6 Tagen schon ein Langvideo geliefert, beendet sich der Lauf ohne neues Video.';
  }
  if (t === 'abholen') {
    // GEMELDET 08.10.2026: Feedback soll gleich im naechsten Lauf wirken, nicht erst nach 4 h.
    const e = await starte(env, 'themen.yml', {});
    return e.includes('bereits aktiv') ? 'Die Abholung laeuft gerade schon.'
      : 'Abholung gestartet: Feedback, Themen, Skripte, Links und Bewertungen aus dem Videobot ' +
        'werden jetzt verarbeitet. Der Videobot bestaetigt in ca. 2-3 Minuten.';
  }
  const m = t.match(/^start(?:\s+(business|ki|ai))?(\s+bezahlt)?$/);
  if (!m) return `„${String(text || '').trim().slice(0, 40)}“ kenne ich nicht.\n\n` + HILFE;
  const heute = new Date().toISOString().slice(0, 10);
  const manuell = (await laeufe(env, `&event=workflow_dispatch&created=%3E%3D${heute}`, 'video.yml', 50))
    .filter((r) => !zeitplanStart(r.created_at)).length;
  if (manuell >= START_MAX) {
    return `Heute schon ${manuell} manuelle Laeufe - Grenze ${START_MAX} (spart Rechenzeit). Morgen geht es weiter.`;
  }
  const kanal = m[1] ? KANAELE[m[1]] : 'alle';
  // 21.10.2026: „bezahlt" nur ausdruecklich nach der Gratis-Meldung - startet trotz leerem Gratis-Kontingent.
  // 23.10.2026: quelle 'hand' - sonst hielt video.yml einen Start kurz nach einem Zeitplan-Cron fuer den Zeitplan.
  const ergebnis = await starte(env, 'video.yml', m[2] ? { kanal, thema: '', bezahlt: 'ja', quelle: 'hand' }
    : { kanal, thema: '', quelle: 'hand' });
  if (ergebnis.includes('bereits aktiv')) return 'Es laeuft gerade schon ein Videolauf - kein Doppelstart. Schreib „Status".';
  return `Gestartet (${kanal}${m[2] ? ', kostenpflichtig erlaubt' : ''}). Ergebnis in ca. 30-45 Minuten ueber den Videobot.\n` +
    'Weitere Videos laufen, solange das kostenlose Kontingent reicht; sonst kommt eine Meldung mit dem Grund.';
}

// ---- Videobot-Eingang (Webhook) -------------------------------------------------
// GEMESSEN 21.10.2026: TikTok-Klicks gingen dreimal verloren - sie lagen bei Telegram (getUpdates zeigte
// tu:d4c7f17bcc706f1b:ok) und waren Minuten spaeter weg, ohne dass themen.py sie bekam; ein zweiter,
// unbekannter getUpdates-Abholer ist die einzige Erklaerung. Mit Webhook liefert Telegram jede Aktualisierung
// genau hierher (ein anderer getUpdates-Aufruf bekommt 409); themen.py holt sie aus dem KV-Speicher ab.
// Ausserdem startet ein Knopfdruck die Abholung sofort statt nach bis zu 5 Minuten.
const vbToken = (env) => String(env.TG_VIDEO_TOKEN || '').trim().replace(/^bot/i, '').replace(/\s+/g, '');
const VB_TTL_S = 7 * 86400;

async function vbGeheimnis(env, zweck) {
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`cf-${zweck}:` + vbToken(env)));
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}

async function videobotEingang(request, env) {
  if (!env.ZUSTAND || !vbToken(env)
      || request.headers.get('X-Telegram-Bot-Api-Secret-Token') !== await vbGeheimnis(env, 'video')) {
    return new Response('verboten', { status: 403 });
  }
  const update = await request.json().catch(() => null);
  if (!update || !Number.isInteger(update.update_id)) return new Response('ok');
  // Sicherheitsbefund 24.10.2026: Fremde, die dem oeffentlichen Videobot schreiben, kosteten je Nachricht einen
  // KV-Schreibvorgang (Gratis ~1000/Tag) und einen themen.yml-Start. themen.py prueft dasselbe Feld gegen
  // TELEGRAM_CHAT_ID. Ohne TG_VIDEO_CHAT_ID bleibt alles wie bisher (kein Klick darf verloren gehen).
  const nachricht = update.message || (update.callback_query || {}).message || {};
  const chat = String((nachricht.chat || {}).id ?? '');
  if (env.TG_VIDEO_CHAT_ID && chat !== String(env.TG_VIDEO_CHAT_ID).trim()) return new Response('ok');
  await env.ZUSTAND.put('vb:' + String(update.update_id).padStart(12, '0'), JSON.stringify(update),
    { expirationTtl: VB_TTL_S });
  // GEMESSEN 31.10.2026: ein TikTok-Knopf kam fuenfmal an (18:04-18:08 UTC) - die Ladeanzeige beendete erst
  // themen.py Minuten spaeter, der Knopf wirkte tot. Jetzt sofort quittieren (themen.py' Antwort laeuft dann ins Leere).
  if (update.callback_query && update.callback_query.id) {
    try {
      await fetch(`https://api.telegram.org/bot${vbToken(env)}/answerCallbackQuery`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ callback_query_id: update.callback_query.id, show_alert: false,
          text: 'Angekommen. Wird in 1-5 Min. verarbeitet, die Antwort kommt hier im Chat. Nicht nochmal tippen.' }),
      });
    } catch (e) { console.log('Knopf-Quittung:', e.message); }
  }
  // Knopf oder Nachricht: Abholer gleich starten (laeuft er schon, holt er es beim naechsten Takt).
  if (env.GH_TOKEN) {
    try { await starte(env, 'themen.yml', { automatisch: 'true' }); } catch (e) { console.log('Abholer-Start:', e.message); }
  }
  return new Response('ok');
}

async function videobotAbholen(request, env) {
  if (!env.ZUSTAND || !vbToken(env) || request.headers.get('X-Abholer') !== await vbGeheimnis(env, 'abholen')) {
    return new Response('verboten', { status: 403 });
  }
  const updates = [];
  let cursor;
  do {
    const seite = await env.ZUSTAND.list({ prefix: 'vb:', cursor });
    for (const k of seite.keys) {
      const wert = await env.ZUSTAND.get(k.name);
      if (wert) updates.push(JSON.parse(wert));
    }
    cursor = seite.list_complete ? undefined : seite.cursor;
  } while (cursor);
  updates.sort((a, b) => a.update_id - b.update_id);
  return Response.json({ ok: true, result: updates });
}

async function telegram(request, env) {
  if (!env.TG_BEFEHL_TOKEN || request.headers.get('X-Telegram-Bot-Api-Secret-Token') !== await geheimnis(env)) {
    return new Response('verboten', { status: 403 });
  }
  const update = await request.json().catch(() => ({}));
  const msg = update.message || {};
  const chat = msg.chat && String(msg.chat.id);
  if (!chat || !msg.text) return new Response('ok');
  if (!env.TG_CHAT_ID) {
    // Einrichtung: Chat-ID ist kein Geheimnis; ohne sie startet nichts.
    await antworten(env, chat, `Einrichtung: deine Chat-ID ist ${chat}. Als Variable TG_CHAT_ID im Worker eintragen.`);
    return new Response('ok');
  }
  if (chat !== String(env.TG_CHAT_ID)) return new Response('ok');  // fremde Chats still ignorieren
  let text;
  try { text = await befehl(env, msg.text); } catch (e) { text = 'Fehler: ' + String(e.message || e).slice(0, 200); }
  await antworten(env, chat, text);
  return new Response('ok');
}

// Nutzerwunsch 15.10.2026: bei 5 EUR Ausgabenobergrenze rechtzeitig per Telegram warnen.
// Google-Budget -> Pub/Sub-Push -> hierher. Google schickt den Stand mehrmals taeglich, auch nach
// ueberschrittener Schwelle immer wieder; ohne Merker (KV) kaeme dieselbe Warnung alle ~20 Minuten.
function kostenText(d, schwelle, prognose) {
  const eur = (x) => Number(x || 0).toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const prozent = Math.round(Number(schwelle) * 100);
  const kopf = prognose
    ? `Warnung Gemini-Kosten: Prognose fuer diesen Monat erreicht ${prozent} % der Grenze.`
    : `Warnung Gemini-Kosten: ${prozent} % der Grenze erreicht.`;
  return `${kopf}\nBisher ${eur(d.costAmount)} € von ${eur(d.budgetAmount)} € (${d.budgetDisplayName || 'Budget'}).\n` +
    'Bei Erreichen der Grenze pausieren bezahlte Stimme und Gemini-Reserve bis zum Monatsersten.\n' +
    // Nutzer 28.10.2026: "den genauen Link, wo ich wieder aufladen muss". Screenshot AI Studio: Rechnungskonto des
    // Projekts contentfabrik-stimme ist VORAUSZAHLUNG (5 EUR am 09.10., automatisches Aufladen aus). Bei 0 EUR
    // Guthaben stoppen die Schluessel dieses Projekts; das Gratis-Projekt laeuft weiter. Im falschen Google-Konto
    // zeigt /billing "No billing account" - dort NICHT "Set up billing" druecken.
    'Bezahlte Stimme laeuft ueber Vorauszahlung: Guthaben wird verbraucht, nicht monatlich erneuert.\n' +
    'Aufladen: https://aistudio.google.com/billing (Google-Konto mit Projekt contentfabrik-stimme)\n' +
    'Monatsgrenze aendern: https://aistudio.google.com/spend';
}

async function kosten(request, env) {
  const t = new URL(request.url).searchParams.get('t') || '';
  if (!env.KOSTEN_TOKEN || t !== String(env.KOSTEN_TOKEN)) return new Response('verboten', { status: 403 });
  // Ohne Merker oder Chat lieber laut scheitern: Pub/Sub wiederholt dann, statt still zu verschlucken.
  if (!env.ZUSTAND || !env.TG_CHAT_ID || !env.TG_BEFEHL_TOKEN) return new Response('nicht eingerichtet', { status: 503 });
  const huelle = await request.json().catch(() => ({}));
  let d;
  try { d = JSON.parse(atob((huelle.message && huelle.message.data) || '')); } catch { return new Response('ok'); }
  const meldungen = [];
  if (d.alertThresholdExceeded != null) meldungen.push([d.alertThresholdExceeded, false]);
  if (d.forecastThresholdExceeded != null) meldungen.push([d.forecastThresholdExceeded, true]);
  for (const [schwelle, prognose] of meldungen) {
    const merker = `kosten:${d.budgetDisplayName}:${d.costIntervalStart}:${prognose ? 'prognose' : 'ist'}:${schwelle}`;
    if (await env.ZUSTAND.get(merker)) continue;
    // Merker erst nach bestaetigter Zustellung; sonst 502 -> Pub/Sub stellt die Meldung erneut zu.
    const r = await antworten(env, String(env.TG_CHAT_ID), kostenText(d, schwelle, prognose));
    if (!r || !r.ok) return new Response('telegram fehlgeschlagen', { status: 502 });
    await env.ZUSTAND.put(merker, '1', { expirationTtl: 40 * 24 * 3600 });
  }
  return new Response('ok');
}

async function einrichten(request, env) {
  if (!env.TG_BEFEHL_TOKEN) return new Response('TG_BEFEHL_TOKEN fehlt', { status: 503 });
  const ziel = new URL(request.url).origin + '/telegram';
  const r = await fetch(`https://api.telegram.org/bot${tgToken(env)}/setWebhook`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: ziel, secret_token: await geheimnis(env), allowed_updates: ['message'] }),
  });
  const d = await r.json().catch(() => ({}));
  // Diagnose ohne den Token zu verraten: Form pruefen (Zahl:Zeichenfolge, ~45 Zeichen).
  const t = tgToken(env);
  const form = /^\d{6,12}:[A-Za-z0-9_-]{30,}$/.test(t) ? 'Form ok' :
    `Form ungueltig (Laenge ${t.length}, Doppelpunkt ${t.includes(':') ? 'ja' : 'nein'}) - Token bei BotFather neu kopieren`;
  return Response.json({ webhook: ziel, ok: d.ok === true, beschreibung: d.description || '', token: form },
    { status: d.ok ? 200 : 502 });
}

export default {
  async scheduled(event, env, ctx) {
    let job;
    // GEMELDET 10.10.2026: Telegram-Bewertungen/-Themen in ~5 Min. statt alle 4 Std. abholen;
    // der GitHub-Zeitplan lief unzuverlaessig. '7 */4' bleibt als Rueckfall gueltig.
    if (event.cron === '*/5 * * * *' || event.cron === '7 */4 * * *') {
      // workflow_dispatch allein bedeutet keinen Nutzerstart: Tagesauswertung weiter nur einmal.
      job = starte(env, 'themen.yml', { automatisch: 'true' });
      // GEMESSEN 14.10.2026: GitHub startete zwischen 00 und 07 UTC nur 2 Zeitplanlaeufe; der
      // Skript-Vorrat (skripte.yml, 01:07/05:07) lief deshalb hoechstens einmal taeglich. Ohne
      // zusaetzlichen Cron-Trigger (Free-Plan: 5 je Konto) im ersten 5-Minuten-Takt um 01 und 05 UTC.
      const zeit = event.scheduledTime ? new Date(event.scheduledTime) : null;
      if (zeit && [1, 5].includes(zeit.getUTCHours()) && zeit.getUTCMinutes() >= 5 && zeit.getUTCMinutes() < 10) {
        const vorrat = starte(env, 'skripte.yml', {});
        job = Promise.all([job, vorrat]).then((t) => t.join(' | '));
      }
      // 16.10.2026: Der Vorrat-Cron 01:07 erschien nie in der Run-Liste - GitHub verschluckt Zeitplaene.
      // Langvideo (Fr-So 12:07 UTC) deshalb 33 Min spaeter nachholen, wenn heute noch kein Lauf existiert.
      // Doppelstart verhindern starte() (aktiver Lauf), die Warteschlange und die Wochensperre der Vorpruefung.
      // Nutzer 22.10.2026: zwei Tage vor dem Hochladen bauen (Sonntagabend), Kontingent entspannt nutzen.
      if (zeit && [5, 6, 0].includes(zeit.getUTCDay()) && zeit.getUTCHours() === 12
          && zeit.getUTCMinutes() >= 40 && zeit.getUTCMinutes() < 45) {
        const heute = zeit.toISOString().slice(0, 10);
        const lang = laeufe(env, '', 'langvideo.yml', 10).then((l) => l.some(r => (r.created_at || '').startsWith(heute))
          ? 'langvideo.yml: heute schon gestartet' : starte(env, 'langvideo.yml', {}));
        job = Promise.all([job, lang]).then((t) => t.join(' | '));
      }
    }
    else if (VIDEO_CRONS.has(event.cron)) job = starte(env, 'video.yml', { kanal: 'alle', thema: '', quelle: 'zeitplan' });
    else throw new Error('Unbekannter Contentfabrik-Zeitplan');
    ctx.waitUntil(job.then((t) => console.log(t)));
  },
  // Oeffentliche Statusseite startet nichts und verraet niemals den Schluessel.
  // Ein vorhandener Secret beweist noch keine GitHub-Berechtigung oder Cron-Ausfuehrung.
  async fetch(request, env = {}) {
    const pfad = request ? new URL(request.url).pathname : '/';
    if (pfad === '/telegram' && request.method === 'POST') return telegram(request, env);
    if (pfad === '/videobot' && request.method === 'POST') return videobotEingang(request, env);
    if (pfad === '/videobot/abholen') return videobotAbholen(request, env);
    if (pfad === '/kosten' && request.method === 'POST') return kosten(request, env);
    if (pfad === '/fortschritt' && request.method === 'POST') return fortschrittEingang(request, env);
    if (pfad === '/einrichten') return einrichten(request, env);
    return Response.json({ worker: 'contentfabrik-zeitplan', version: VERSION, repository: REPO,
      github_schluessel_vorhanden: Boolean(env.GH_TOKEN),
      hinweis: 'GitHub-Berechtigung und Cron-Ausfuehrung separat pruefen; kein Video-Start durch diese URL.' },
    { status: env.GH_TOKEN ? 200 : 503 });
  },
};
