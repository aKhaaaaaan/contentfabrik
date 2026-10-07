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

const REPO = 'aKhaaaaaan/contentfabrik';
const VERSION = '2026-10-07.1';
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
    return Response.json({ worker: 'contentfabrik-zeitplan', version: VERSION, repository: REPO,
      github_schluessel_vorhanden: Boolean(env.GH_TOKEN),
      hinweis: 'GitHub-Berechtigung und Cron-Ausfuehrung separat pruefen; kein Video-Start durch diese URL.' },
    { status: env.GH_TOKEN ? 200 : 503 });
  },
};
