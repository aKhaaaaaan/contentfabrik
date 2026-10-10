import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const code = await readFile(new URL('../cloudflare/zeitplan-worker.js', import.meta.url), 'utf8');
const { default: worker } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const original = globalThis.fetch;
let anfragen = [];
let job;
let runs = [];
const ctx = { waitUntil(p) { job = p; } };
const start = async (cron, env = { GH_TOKEN: 'test' }) => {
  await worker.scheduled({ cron }, env, ctx);
  await job;
};

try {
  globalThis.fetch = async (url, options) => {
    anfragen.push({ url, options });
    if (url.includes('/runs?')) return { ok: true, status: 200, json: async () => ({workflow_runs:runs}) };
    return { ok: true, status: 204 };
  };
  await start('23 8 * * *');
  const versand = anfragen.filter(a => a.options.method === 'POST');
  assert.ok(versand[0].url.endsWith('/video.yml/dispatches'));
  assert.deepEqual(JSON.parse(versand[0].options.body), { ref: 'main', inputs: { kanal: 'alle', thema: '' } });
  assert.equal(anfragen[0].options.headers['Content-Type'], 'application/json');
  await start('7 */4 * * *');
  assert.ok(anfragen.filter(a => a.options.method === 'POST')[1].url.endsWith('/themen.yml/dispatches'));
  await start('*/5 * * * *');  // 10.10.2026: Abholung alle 5 Minuten
  assert.ok(anfragen.filter(a => a.options.method === 'POST')[2].url.endsWith('/themen.yml/dispatches'));
  for (const cron of ['23 8,13 * * *', '41 10,15 * * *']) {
    await start(cron);
    assert.ok(anfragen.at(-1).url.endsWith('/video.yml/dispatches'));
  }
  await assert.rejects(start('23 8 * * *', {}), /GH_TOKEN fehlt/);
  const vorher=anfragen.filter(a=>a.options.method==='POST').length;
  for(const status of ['queued','pending','in_progress','waiting','requested']) {
    runs=[{status}]; await start('23 8 * * *');
  }
  assert.equal(anfragen.filter(a=>a.options.method==='POST').length,vorher);
  runs=[];
  await assert.rejects(start('9 9 * * *'),/Unbekannter/);
  globalThis.fetch = async () => ({ ok: false, status: 403 });
  await assert.rejects(start('23 8 * * *'), /HTTP 403/);
  const fehlt=await worker.fetch(); assert.equal(fehlt.status,503);
  assert.equal((await fehlt.json()).github_schluessel_vorhanden,false);
  const status=await worker.fetch(undefined,{GH_TOKEN:'SECRET_NOT_FOR_OUTPUT'});
  assert.equal(status.status,200);
  assert.ok(!(await status.text()).includes('SECRET_NOT_FOR_OUTPUT'));
  console.log('Zeitplan-Pruefungen bestanden: Dispatch, kompakte Cron-Zeiten, fuenf aktive Laufzustaende, Fehler, Secret-Status.');
} finally {
  globalThis.fetch = original;
}
