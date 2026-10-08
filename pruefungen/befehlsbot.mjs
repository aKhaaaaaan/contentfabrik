// Befehls-Bot im Zeitplan-Worker (Nutzerwunsch 08.10.2026): Start/Status per Telegram.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const code = await readFile(new URL('../cloudflare/zeitplan-worker.js', import.meta.url), 'utf8');
const { default: worker } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const original = globalThis.fetch;
const ENV = { GH_TOKEN: 'gh', TG_BEFEHL_TOKEN: '123:abc', TG_CHAT_ID: '42' };
let anfragen, runs, heuteManuell, jobs;

async function geheim(token) {
  const h = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('cf-befehl:' + token));
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 48);
}
async function senden(text, { chat = 42, env = ENV, schluessel } = {}) {
  anfragen = [];
  const kopf = { 'X-Telegram-Bot-Api-Secret-Token': schluessel ?? await geheim(env.TG_BEFEHL_TOKEN) };
  const req = new Request('https://w.example/telegram', { method: 'POST', headers: kopf,
    body: JSON.stringify({ message: { chat: { id: chat }, text } }) });
  return worker.fetch(req, env);
}
const antwort = () => JSON.parse(anfragen.find(a => a.url.includes('/sendMessage'))?.options.body || '{}').text;
const gestartet = () => anfragen.filter(a => a.url.endsWith('/dispatches'));

try {
  globalThis.fetch = async (url, options = {}) => {
    anfragen.push({ url, options });
    if (url.includes('event=workflow_dispatch')) return { ok: true, json: async () => ({ workflow_runs: Array(heuteManuell).fill({}) }) };
    if (url.includes('/runs?')) return { ok: true, json: async () => ({ workflow_runs: runs }) };
    if (url.includes('/jobs')) return { ok: true, json: async () => ({ jobs }) };
    if (url.includes('setWebhook')) return { ok: true, json: async () => ({ ok: true }) };
    return { ok: true, status: 204, json: async () => ({ ok: true }) };
  };
  runs = []; heuteManuell = 0; jobs = [];

  // Fremde Aufrufer ohne richtiges Webhook-Geheimnis: nichts passiert.
  assert.equal((await senden('Start', { schluessel: 'falsch' })).status, 403);
  assert.equal(gestartet().length, 0);

  // Einrichtung ohne TG_CHAT_ID: nur die eigene Chat-ID nennen, nichts starten.
  await senden('Start', { env: { GH_TOKEN: 'gh', TG_BEFEHL_TOKEN: '123:abc' }, chat: 77 });
  assert.match(antwort(), /Chat-ID ist 77/);
  assert.equal(gestartet().length, 0);

  // Fremder Chat: still ignorieren.
  await senden('Start', { chat: 99 });
  assert.equal(gestartet().length, 0);
  assert.equal(antwort(), undefined);

  // Start Business aus dem eigenen Chat.
  await senden('Start Business');
  assert.equal(gestartet().length, 1);
  assert.deepEqual(JSON.parse(gestartet()[0].options.body).inputs, { kanal: 'business-origin-stories', thema: '' });
  assert.match(antwort(), /Gestartet/);

  // Tagesgrenze: kein weiterer Start.
  heuteManuell = 6;
  await senden('Start');
  assert.equal(gestartet().length, 0);
  assert.match(antwort(), /Grenze 6/);
  heuteManuell = 0;

  // /start beim ersten Oeffnen des Bots startet NICHTS, sondern zeigt die Hilfe.
  await senden('/start');
  assert.equal(gestartet().length, 0);
  assert.match(antwort(), /Befehle/);

  // Abholen startet sofort die Themen-/Feedback-Abholung.
  runs = [];
  await senden('Abholen');
  assert.ok(gestartet()[0].url.endsWith('/themen.yml/dispatches'));
  assert.match(antwort(), /Abholung gestartet/);

  // Status mit Schaetzung: 15 von 30 Minuten Produktion = 50 %.
  runs = [{ id: 1, status: 'in_progress', created_at: new Date().toISOString(), html_url: 'u' }];
  jobs = [{ name: 'video (ai-tools-explained)', status: 'in_progress', steps: [
    { name: 'Erzeugen, pruefen, lernen, senden', status: 'in_progress',
      started_at: new Date(Date.now() - 15 * 60000).toISOString() }] }];
  await senden('Status');
  assert.match(antwort(), /ai-tools-explained/);
  assert.match(antwort(), /Gesamt: ca\. 50 %/);   // 10 % + 80 % * 15/30
  // Zwei Kanaele: AI fertig, Business halb durch -> (1 + 0.5) / 2 = 75 %.
  jobs = [{ name: 'video (ai-tools-explained)', status: 'completed', steps: [] },
          { name: 'video (business-origin-stories)', status: 'in_progress', steps: [
            { name: 'Erzeugen, pruefen, lernen, senden', status: 'in_progress',
              started_at: new Date(Date.now() - 15 * 60000).toISOString() }] }];
  await senden('Status');
  assert.match(antwort(), /Gesamt: ca\. 75 %/);
  assert.match(antwort(), /Schon fertig: ai-tools-explained/);

  // Einrichtung des Webhooks auf die eigene Worker-Adresse mit abgeleitetem Geheimnis.
  anfragen = [];
  const e = await worker.fetch(new Request('https://w.example/einrichten'), ENV);
  assert.equal(e.status, 200);
  const hook = JSON.parse(anfragen[0].options.body);
  assert.equal(hook.url, 'https://w.example/telegram');
  assert.equal(hook.secret_token, await geheim('123:abc'));
  console.log('Befehls-Bot-Pruefungen bestanden: Geheimnis, Einrichtung, fremder Chat, Start, Grenze, /start, Status, Webhook.');
} finally {
  globalThis.fetch = original;
}
