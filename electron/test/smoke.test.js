'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { runSmoke } = require('../src/smoke');

function startServer(routes) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const route = routes[req.url];
      if (!route) {
        res.writeHead(404);
        res.end();
        return;
      }
      res.writeHead(route.status, { 'content-type': 'text/html' });
      res.end(route.body);
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

test('runSmoke true for health 200 + title page', async (t) => {
  const server = await startServer({
    '/_stcore/health': { status: 200, body: 'ok' },
    '/': { status: 200, body: '<!doctype html><html><head><title>Finance</title></head></html>' },
  });
  t.after(() => server.close());
  const { port } = server.address();
  assert.equal(await runSmoke(`http://127.0.0.1:${port}/`), true);
});

test('runSmoke false when / lacks <title', async (t) => {
  const server = await startServer({
    '/_stcore/health': { status: 200, body: 'ok' },
    '/': { status: 200, body: '<html><body>no title here</body></html>' },
  });
  t.after(() => server.close());
  const { port } = server.address();
  assert.equal(await runSmoke(`http://127.0.0.1:${port}/`), false);
});

test('runSmoke false on connection refused', async (t) => {
  const server = await startServer({});
  const { port } = server.address();
  await new Promise((resolve) => server.close(resolve));
  assert.equal(await runSmoke(`http://127.0.0.1:${port}/`, { timeoutMs: 2000 }), false);
});
