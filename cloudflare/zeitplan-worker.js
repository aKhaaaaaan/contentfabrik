// Puenktlicher Zeitplan fuer die Contentfabrik (Cloudflare Workers, Cron Triggers - kostenlos).
//
// GEMESSEN 04./05.10.2026: GitHub startete die zeitgesteuerten Laeufe 7 Stunden zu spaet
// bzw. gar nicht ("schedule events may be delayed during periods of high load").
// Dieser Worker stoesst den Lauf zur Minute genau ueber die offizielle GitHub-Schnittstelle
// an (workflow_dispatch). kanal=alle -> die Vorpruefung nimmt nur Kanaele ohne Video mit 8+.
//
// Einrichtung (einmalig, Cloudflare-Dashboard -> Workers & Pages -> Create -> Worker):
//   1. diesen Code einfuegen
//   2. Settings -> Variables and Secrets -> Secret GH_TOKEN = GitHub-Fine-grained-Token
//      (nur Repository aKhaaaaaan/contentfabrik, nur "Actions: Read and write")
//   3. Settings -> Triggers -> Cron Triggers (UTC): 23 8 * * *, 41 10 * * *, 23 13 * * *, 41 15 * * *
//      und fuer die Themen-Abholung: 7 */4 * * *

const REPO = 'aKhaaaaaan/contentfabrik';

async function starte(env, workflow, inputs) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.GH_TOKEN}`,
      Accept: 'application/vnd.github+json',
      'User-Agent': 'contentfabrik-zeitplan',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({ ref: 'main', inputs }),
  });
  return `${workflow}: ${r.status}`;
}

export default {
  async scheduled(event, env, ctx) {
    // Minute 7 = Themen abholen (alle 4 Stunden), sonst Video-Lauf fuer alle offenen Kanaele
    const job = event.cron.startsWith('7 ')
      ? starte(env, 'themen.yml', {})
      : starte(env, 'video.yml', { kanal: 'alle', thema: '' });
    ctx.waitUntil(job.then((t) => console.log(t)));
  },
  // Zum Testen im Browser: /status zeigt nur, dass der Worker laeuft (kein Start)
  async fetch() {
    return new Response('Contentfabrik-Zeitplan aktiv', { headers: { 'content-type': 'text/plain' } });
  },
};
