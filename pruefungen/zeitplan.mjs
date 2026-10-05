import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const code = await readFile(new URL('../cloudflare/zeitplan-worker.js', import.meta.url), 'utf8');
const { default: worker } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const original = globalThis.fetch;
let anfragen = [];
let job;
const ctx = { waitUntil(p) { job = p; } };
const start = async (cron, env = { GH_TOKEN: 'test' }) => {
  await worker.scheduled({ cron }, env, ctx);
  await job;
};

try {
  globalThis.fetch = async (url, options) => {
    anfragen.push({ url, options });
    return { ok: true, status: 204 };
  };
  await start('23 8 * * *');
  assert.ok(anfragen[0].url.endsWith('/video.yml/dispatches'));
  assert.deepEqual(JSON.parse(anfragen[0].options.body), { ref: 'main', inputs: { kanal: 'alle', thema: '' } });
  assert.equal(anfragen[0].options.headers['Content-Type'], 'application/json');
  await start('7 */4 * * *');
  assert.ok(anfragen[1].url.endsWith('/themen.yml/dispatches'));
  await assert.rejects(start('23 8 * * *', {}), /GH_TOKEN fehlt/);
  globalThis.fetch = async () => ({ ok: false, status: 403 });
  await assert.rejects(start('23 8 * * *'), /HTTP 403/);
  assert.equal((await worker.fetch()).status, 200);
  console.log('Zeitplan: 5 Pruefungen bestanden');
} finally {
  globalThis.fetch = original;
}
