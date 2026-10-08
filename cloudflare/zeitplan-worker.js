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
//      und fuer die Themen-Abholung: 7 */4 * * *
//
// Befehls-Bot (08.10.2026): zweiter Telegram-Bot nur fuer Start/Status.
//   4. @BotFather -> /newbot -> Token als Secret TG_BEFEHL_TOKEN eintragen
//   5. <worker-url>/einrichten einmal im Browser oeffnen (setzt den Webhook)
//   6. dem neuen Bot „Hallo" schreiben -> er nennt die Chat-ID -> Variable TG_CHAT_ID
//   Befehle: Start | Start Business | Start KI | Status (Gesamtfortschritt in %) | Abholen

const REPO = 'aKhaaaaaan/contentfabrik';
const VERSION = '2026-10-08.2';
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
  if (daten.workflow_runs.some(r => ['queued', 'pending', 'in_progress', 'waiting', 'requested'].includes(r.status))) {
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
const START_MAX = 6;
const KANAELE = { business: 'business-origin-stories', ki: 'ai-tools-explained', ai: 'ai-tools-explained' };
const HILFE = 'Befehle:\nStart - beide Kanaele\nStart Business - nur Business Origin Stories\n' +
  'Start KI - nur AI Tools Explained\nStatus - Fortschritt in Prozent\n' +
  'Abholen - Feedback/Themen aus dem Videobot sofort verarbeiten\n\n' +
  'Feedback gibst du im Videobot: auf ein Video antworten oder „Feedback: ..." schreiben.';

// GEMESSEN 08.10.2026: Am Handy eingefuegter Token -> Telegram 'Not Found' (ungueltig).
// Leerzeichen/Zeilenumbrueche und ein mitkopiertes 'bot' davor entfernen.
const tgToken = (env) => String(env.TG_BEFEHL_TOKEN || '').trim().replace(/^bot/i, '').replace(/\s+/g, '');

async function geheimnis(env) {
  // Webhook-Schutz ohne weiteres Secret: aus dem Bot-Token abgeleitet (A-Z, a-z, 0-9 erlaubt).
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('cf-befehl:' + tgToken(env)));
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}

async function antworten(env, chat, text) {
  await fetch(`https://api.telegram.org/bot${tgToken(env)}/sendMessage`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: chat, text }),
  });
}

function ghKopf(env) {
  return { Authorization: `Bearer ${env.GH_TOKEN}`, Accept: 'application/vnd.github+json',
    'User-Agent': 'contentfabrik-zeitplan', 'X-GitHub-Api-Version': '2022-11-28' };
}

async function laeufe(env, zusatz = '') {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/video.yml/runs?per_page=20${zusatz}`,
    { headers: ghKopf(env) });
  if (!r.ok) throw new Error(`Status HTTP ${r.status}`);
  return (await r.json()).workflow_runs || [];
}

const berlin = (iso) => new Date(iso).toLocaleTimeString('de-DE',
  { timeZone: 'Europe/Berlin', hour: '2-digit', minute: '2-digit' });

// GEMELDET 08.10.2026: „Ein Status-Wort, zum Beispiel noch 60 % bei Bildgenerierung."
// Grundversion: aktueller GitHub-Schritt + Zeit. Die Produktion hat hoechstens 30 Minuten
// (BUDGET_S), daraus eine ehrliche Schaetzung - keine gemessene Bildzahl.
const PRODUKTION_MIN = 30;

export async function fortschritt(env, lauf) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/runs/${lauf.id}/jobs`, { headers: ghKopf(env) });
  const jobs = r.ok ? ((await r.json()).jobs || []) : [];
  // GEMELDET 08.10.2026: „Gesamte Pipeline in Prozent." Je Kanal: Einrichtung 0-10 %,
  // Produktion 10-90 % (nach Zeit, max. 30 Min), Sichern/Versand 90-100 %; Kanaele zu gleichen Teilen.
  const kanaljobs = jobs.filter(j => j.name.startsWith('video ('));
  const job = jobs.find(j => j.status === 'in_progress');
  const name = j => j.name.replace(/^video \((.*)\)$/, '$1');
  if (!job) return `Gesamt: 0 % - Lauf wartet auf einen freien Rechner (seit ${berlin(lauf.created_at)}).\n${lauf.html_url}`;
  const schritte = job.steps || [];
  const schritt = schritte.find(s => s.status === 'in_progress');
  const produktion = schritte.find(s => s.name.startsWith('Erzeugen'));
  let anteil = 0.05, zeile = '';
  if (produktion && produktion.status === 'completed') anteil = 0.95;
  else if (schritt && schritt.name.startsWith('Erzeugen')) {
    const minuten = Math.max(0, (Date.now() - new Date(schritt.started_at)) / 60000);
    anteil = 0.1 + 0.8 * Math.min(1, minuten / PRODUKTION_MIN);
    zeile = `\nSkript, Stimme, Bilder, Pruefung laufen seit ${Math.round(minuten)} Min`;
  }
  const fertig = kanaljobs.filter(j => j.status === 'completed');
  const gesamt = kanaljobs.length || 1;
  const prozent = Math.min(99, Math.round((fertig.length + anteil) / gesamt * 100));
  let text = `Gesamt: ca. ${prozent} % (geschaetzt)\nJetzt: ${name(job)} - ${schritt ? schritt.name : 'Vorbereitung'}` + zeile;
  if (fertig.length) text += `\nSchon fertig: ${fertig.map(name).join(', ')}`;
  return text + `\n${lauf.html_url}`;
}

export async function befehl(env, text) {
  const t = String(text || '').trim().toLowerCase();
  if (t === 'status') {
    const rs = (await laeufe(env)).slice(0, 4);
    if (!rs.length) return 'Noch keine Videolaeufe.';
    const aktiv = rs.find(r => r.status !== 'completed');
    if (aktiv) return await fortschritt(env, aktiv);
    return 'Letzte Videolaeufe:\n' + rs.map(r => `${berlin(r.created_at)} - ${
      r.status === 'completed' ? (r.conclusion === 'success' ? 'beendet' : 'Fehler') : 'laeuft/wartet'}\n${r.html_url}`)
      .join('\n') + '\n\n„Beendet" heisst nicht automatisch Video - das Ergebnis meldet der Videobot.';
  }
  if (t === 'abholen') {
    // GEMELDET 08.10.2026: Feedback soll gleich im naechsten Lauf wirken, nicht erst nach 4 h.
    const e = await starte(env, 'themen.yml', {});
    return e.includes('bereits aktiv') ? 'Die Abholung laeuft gerade schon.'
      : 'Abholung gestartet: Feedback, Themen, Skripte, Links und Bewertungen aus dem Videobot ' +
        'werden jetzt verarbeitet. Der Videobot bestaetigt in ca. 2-3 Minuten.';
  }
  const m = t.match(/^start(?:\s+(business|ki|ai))?$/);
  if (!m) return HILFE;
  const heute = new Date().toISOString().slice(0, 10);
  const manuell = (await laeufe(env, `&event=workflow_dispatch&created=%3E%3D${heute}`)).length;
  if (manuell >= START_MAX) {
    return `Heute schon ${manuell} manuelle Laeufe - Grenze ${START_MAX} (spart Rechenzeit). Morgen geht es weiter.`;
  }
  const kanal = m[1] ? KANAELE[m[1]] : 'alle';
  const ergebnis = await starte(env, 'video.yml', { kanal, thema: '' });
  if (ergebnis.includes('bereits aktiv')) return 'Es laeuft gerade schon ein Videolauf - kein Doppelstart. Schreib „Status".';
  return `Gestartet (${kanal}). Ergebnis in ca. 30-45 Minuten ueber den Videobot.\n` +
    'Hat ein Kanal heute schon ein Video oder kein Tagesbudget mehr, ueberspringt ihn die Vorpruefung.';
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
    if (event.cron === '7 */4 * * *') job = starte(env, 'themen.yml', {});
    else if (VIDEO_CRONS.has(event.cron)) job = starte(env, 'video.yml', { kanal: 'alle', thema: '' });
    else throw new Error('Unbekannter Contentfabrik-Zeitplan');
    ctx.waitUntil(job.then((t) => console.log(t)));
  },
  // Oeffentliche Statusseite startet nichts und verraet niemals den Schluessel.
  // Ein vorhandener Secret beweist noch keine GitHub-Berechtigung oder Cron-Ausfuehrung.
  async fetch(request, env = {}) {
    const pfad = request ? new URL(request.url).pathname : '/';
    if (pfad === '/telegram' && request.method === 'POST') return telegram(request, env);
    if (pfad === '/einrichten') return einrichten(request, env);
    return Response.json({ worker: 'contentfabrik-zeitplan', version: VERSION, repository: REPO,
      github_schluessel_vorhanden: Boolean(env.GH_TOKEN),
      hinweis: 'GitHub-Berechtigung und Cron-Ausfuehrung separat pruefen; kein Video-Start durch diese URL.' },
    { status: env.GH_TOKEN ? 200 : 503 });
  },
};
