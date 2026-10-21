'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  ServerStartError,
  buildArgs,
  buildEnv,
  findFreePort,
  startServer,
} = require('../src/server-process');

const APP_ROOT = path.resolve(__dirname, '..', '..');
const APP_PY = path.join(APP_ROOT, 'src', 'finance_mosaix', 'dashboard', 'app.py');
const TIMEOUT_MS = 10000;
const KEEP_ALIVE = 'setInterval(() => {}, 1000);';

// Fake "python": `node -e <body> --`. The arguments after `--` (the buildArgsFn result) end up in
// process.argv from index 1 on and are read by the script as `args`.
const fake = (body) => [process.execPath, '-e', `const args = process.argv.slice(1);\n${body}`, '--'];
const PORT = "const port = Number(args[args.indexOf('--server.port') + 1]);";
const argsFor = (_root, port) => ['--server.port', String(port)];

// HTTP server on `port` that answers 200 on /_stcore/health when `condition` (JS expression) holds, else 503.
const healthServer = (condition) => `const http = require('node:http');
const started = Date.now();
http.createServer((req, res) => {
  const ready = req.url === '/_stcore/health' && (${condition});
  res.writeHead(ready ? 200 : 503);
  res.end();
}).listen(port, '127.0.0.1');`;

function tmpDir(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'server-process-test-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  return dir;
}

async function assertDead(pid) {
  const deadline = Date.now() + 2000;
  for (;;) {
    try {
      process.kill(pid, 0);
    } catch {
      return;
    }
    if (Date.now() > deadline) assert.fail(`process ${pid} is still alive`);
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

test('buildArgs contains app.py path and port', () => {
  const args = buildArgs(APP_ROOT, 8123);
  assert.deepEqual(args.slice(0, 4), ['-m', 'streamlit', 'run', APP_PY]);
  assert.equal(args[args.indexOf('--server.port') + 1], '8123');
  assert.equal(args[args.indexOf('--server.address') + 1], '127.0.0.1');
  assert.equal(args[args.indexOf('--server.headless') + 1], 'true');
  assert.equal(args[args.indexOf('--server.fileWatcherType') + 1], 'none');
});

test('buildEnv sets PYTHONPATH to src, drops PYTHONHOME case-insensitively, sets data dir', () => {
  const env = buildEnv({ PythonHome: '/x', PYTHONHOME: '/y', PATH: '/bin' }, { appRoot: APP_ROOT, dataDir: '/data' });
  assert.equal(env.PYTHONPATH, path.join(APP_ROOT, 'src'));
  assert.equal(env.PYTHONNOUSERSITE, '1');
  assert.equal(env.PYTHONUNBUFFERED, '1');
  assert.equal(env.PYTHONUTF8, '1');
  assert.equal(env.PATH, '/bin');
  assert.equal(Object.keys(env).some((key) => key.toUpperCase() === 'PYTHONHOME'), false);
  assert.equal(env.FINANCE_MOSAIX_DATA_DIR, '/data');
});

test('buildEnv keeps an inherited FINANCE_MOSAIX_DATA_DIR when dataDir is null', () => {
  const env = buildEnv({ FINANCE_MOSAIX_DATA_DIR: '/inherited' }, { appRoot: APP_ROOT, dataDir: null });
  assert.equal(env.FINANCE_MOSAIX_DATA_DIR, '/inherited');
});

test('findFreePort returns a port that can be bound', async () => {
  const port = await findFreePort();
  assert.equal(typeof port, 'number');
  assert.ok(port > 0 && port < 65536);
});

test('startServer resolves once health returns 200', async (t) => {
  const python = fake(`${PORT}\n${healthServer('true')}\n${KEEP_ALIVE}`);
  const server = await startServer({ python, appRoot: APP_ROOT, dataDir: null, timeoutMs: TIMEOUT_MS, buildArgsFn: argsFor });
  t.after(() => server.stop());
  assert.equal(server.url, `http://127.0.0.1:${server.port}/`);
  assert.equal(typeof server.pid, 'number');
});

test('startServer keeps polling until health turns 200', async (t) => {
  const python = fake(`${PORT}\n${healthServer('Date.now() - started >= 2000')}\n${KEEP_ALIVE}`);
  const began = Date.now();
  const server = await startServer({ python, appRoot: APP_ROOT, dataDir: null, timeoutMs: TIMEOUT_MS, buildArgsFn: argsFor });
  t.after(() => server.stop());
  assert.ok(Date.now() - began >= 1500, 'must wait while health answers 503');
});

test("startServer retries with a new port on 'Port 8501 is already in use'", async (t) => {
  const python = fake(`${PORT}
if (port === 8501) {
  process.stderr.write('Port 8501 is already in use\\n');
  process.exit(1);
}
${healthServer('true')}
${KEEP_ALIVE}`);
  const ports = [8501, 4321];
  const server = await startServer({
    python, appRoot: APP_ROOT, dataDir: null, timeoutMs: TIMEOUT_MS, buildArgsFn: argsFor,
    deps: { findFreePort: async () => ports.shift() },
  });
  t.after(() => server.stop());
  assert.equal(server.port, 4321);
  assert.equal(server.url, 'http://127.0.0.1:4321/');
});

test('startServer rejects with ServerStartError and tail on early exit', async () => {
  const python = fake(`process.stderr.write('boom\\n'); process.exit(1);`);
  const started = Date.now();
  await assert.rejects(
    startServer({ python, appRoot: APP_ROOT, dataDir: null, timeoutMs: TIMEOUT_MS, buildArgsFn: argsFor }),
    (err) => {
      assert.ok(err instanceof ServerStartError);
      assert.ok(err instanceof Error);
      assert.match(err.stderrTail, /boom/);
      return true;
    },
  );
  assert.ok(Date.now() - started < 5000, 'must not wait until timeoutMs');
});

test('startServer rejects on timeout and kills the process', async (t) => {
  const pidFile = path.join(tmpDir(t), 'pid');
  const python = fake(`require('node:fs').writeFileSync(${JSON.stringify(pidFile)}, String(process.pid));
${KEEP_ALIVE}`);
  await assert.rejects(
    startServer({ python, appRoot: APP_ROOT, dataDir: null, timeoutMs: 500, buildArgsFn: argsFor }),
    (err) => err instanceof ServerStartError,
  );
  const pid = Number(fs.readFileSync(pidFile, 'utf8'));
  assert.throws(() => process.kill(pid, 0));
});

test('stop terminates the process and its children', { skip: process.platform === 'win32' }, async (t) => {
  const pidFile = path.join(tmpDir(t), 'kid-pid');
  const python = fake(`${PORT}
const kid = require('node:child_process').spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore' });
require('node:fs').writeFileSync(${JSON.stringify(pidFile)}, String(kid.pid));
${healthServer('true')}
${KEEP_ALIVE}`);
  const server = await startServer({ python, appRoot: APP_ROOT, dataDir: null, timeoutMs: TIMEOUT_MS, buildArgsFn: argsFor });
  t.after(() => server.stop());
  const kidPid = Number(fs.readFileSync(pidFile, 'utf8'));
  await server.stop();
  await assertDead(kidPid);
  await server.stop();
});

test('handle.onExit fires with code and tail when the process dies after ready', async (t) => {
  const python = fake(`${PORT}
setTimeout(() => {
  process.stderr.write('fatal error\\n');
  process.exit(7);
}, 1000);
${healthServer('true')}`);
  const server = await startServer({ python, appRoot: APP_ROOT, dataDir: null, timeoutMs: TIMEOUT_MS, buildArgsFn: argsFor });
  t.after(() => server.stop());
  const info = await new Promise((resolve) => server.onExit(resolve));
  assert.equal(info.code, 7);
  assert.match(info.tail, /fatal error/);
});

test('startServer works with an appRoot containing spaces and umlauts', async (t) => {
  const appRoot = path.join(tmpDir(t), 'Finance Mosaix Größe Ä');
  fs.mkdirSync(appRoot);
  const python = fake(`${PORT}
if (process.env.PYTHONPATH !== ${JSON.stringify(path.join(appRoot, 'src'))}) process.exit(4);
${healthServer('true')}
${KEEP_ALIVE}`);
  const server = await startServer({ python, appRoot, dataDir: null, timeoutMs: TIMEOUT_MS, buildArgsFn: argsFor });
  t.after(() => server.stop());
  assert.equal(typeof server.port, 'number');
});
