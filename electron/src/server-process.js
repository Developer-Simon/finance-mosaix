'use strict';

const { t } = require('./i18n');
const { spawn, execFile } = require('node:child_process');
const net = require('node:net');
const path = require('node:path');
const readline = require('node:readline');

const DEFAULT_TIMEOUT_MS = 60000;
const STOP_GRACE_MS = 3000;
const TAIL_LINES = 20;
const HEALTH_INTERVAL_MS = 250;
const HEALTH_REQUEST_TIMEOUT_MS = 2000;
const MAX_ATTEMPTS = 3;
const ADDR_IN_USE_RE = /Port \d+ is already in use|Address already in use|WinError 10048|EADDRINUSE/;

class ServerStartError extends Error {
  /**
   * @param {string} message
   * @param {string} stderrTail last lines of the server output
   */
  constructor(message, stderrTail) {
    super(message);
    this.name = 'ServerStartError';
    this.stderrTail = stderrTail;
  }
}

/**
 * Asks the OS for a free TCP port by binding to port 0 and closing again.
 * @param {string} [host]
 * @returns {Promise<number>}
 */
function findFreePort(host = '127.0.0.1') {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, host, () => {
      const { port } = server.address();
      server.close((err) => (err ? reject(err) : resolve(port)));
    });
  });
}

/**
 * Streamlit arguments for the dashboard app.
 * @param {string} appRoot
 * @param {number} port
 * @returns {string[]}
 */
function buildArgs(appRoot, port) {
  return [
    '-m',
    'streamlit',
    'run',
    path.join(appRoot, 'src', 'finance_mosaix', 'dashboard', 'app.py'),
    '--server.headless',
    'true',
    '--server.address',
    '127.0.0.1',
    '--server.port',
    String(port),
    '--browser.gatherUsageStats',
    'false',
    '--server.fileWatcherType',
    'none',
    '--global.developmentMode',
    'false',
  ];
}

/**
 * Child environment: isolated from the user's Python, PYTHONHOME removed (case-insensitive).
 * An inherited FINANCE_MOSAIX_DATA_DIR is kept when dataDir is null.
 * @param {object} baseEnv
 * @param {{ appRoot: string, dataDir: string | null }} options
 * @returns {object}
 */
function buildEnv(baseEnv, { appRoot, dataDir }) {
  const env = {
    ...baseEnv,
    PYTHONPATH: path.join(appRoot, 'src'),
    PYTHONNOUSERSITE: '1',
    PYTHONUNBUFFERED: '1',
    PYTHONUTF8: '1',
  };
  for (const key of Object.keys(env)) {
    if (key.toUpperCase() === 'PYTHONHOME') delete env[key];
  }
  if (dataDir) env.FINANCE_MOSAIX_DATA_DIR = dataDir;
  return env;
}

function killGroup(pid, signal) {
  try {
    process.kill(-pid, signal);
  } catch {
    // group already gone
  }
}

/**
 * Stops the process tree: SIGTERM to the process group, SIGKILL after STOP_GRACE_MS (POSIX);
 * taskkill /T /F on Windows.
 * @param {import('node:child_process').ChildProcess} child
 * @param {Promise<void>} exited resolves on the child's 'close'
 */
async function terminate(child, exited) {
  if (process.platform === 'win32') {
    await new Promise((resolve) => {
      execFile('taskkill', ['/pid', String(child.pid), '/T', '/F'], { windowsHide: true }, () => resolve());
    });
    child.kill();
    await exited;
    return;
  }
  killGroup(child.pid, 'SIGTERM');
  const forceTimer = setTimeout(() => killGroup(child.pid, 'SIGKILL'), STOP_GRACE_MS);
  await exited;
  clearTimeout(forceTimer);
}

async function probeHealth(url, fetchFn) {
  try {
    const response = await fetchFn(`${url}_stcore/health`, {
      signal: AbortSignal.timeout(HEALTH_REQUEST_TIMEOUT_MS),
    });
    await response.arrayBuffer().catch(() => {});
    return response.status === 200;
  } catch {
    return false;
  }
}

/**
 * One start attempt on `port`. Always resolves, never throws.
 * @returns {Promise<
 *   { ok: true, child: import('node:child_process').ChildProcess, exited: Promise<void>,
 *     port: number, url: string, lifecycle: object } |
 *   { ok: false, tail: string, code: number | null, signal: string | null, timedOut: boolean, error: Error | null }
 * >}
 */
function runAttempt(opts, port) {
  const { file, prefix, appRoot, dataDir, buildArgsFn, timeoutMs, fetchFn } = opts;
  const url = `http://127.0.0.1:${port}/`;
  const child = spawn(file, [...prefix, ...buildArgsFn(appRoot, port)], {
    cwd: appRoot,
    env: buildEnv(process.env, { appRoot, dataDir }),
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    detached: process.platform !== 'win32',
  });

  const tail = [];
  const tailText = () => tail.join('\n');
  const pushLine = (line) => {
    tail.push(line);
    if (tail.length > TAIL_LINES) tail.shift();
  };
  readline.createInterface({ input: child.stdout }).on('line', pushLine);
  readline.createInterface({ input: child.stderr }).on('line', pushLine);

  const lifecycle = { ready: false, stopRequested: false, exitListeners: [] };
  let exitInfo = { code: null, signal: null };
  const exited = new Promise((resolve) => {
    child.once('close', (code, signal) => {
      exitInfo = { code, signal };
      if (lifecycle.ready && !lifecycle.stopRequested) {
        for (const cb of lifecycle.exitListeners) cb({ code, signal, tail: tailText() });
      }
      resolve();
    });
  });

  return new Promise((resolve) => {
    let settled = false;
    let polling = false;
    let timer = null;
    let poll = null;

    const settle = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearInterval(poll);
      resolve(result);
    };

    child.once('error', (error) => {
      settle({ ok: false, tail: tailText(), code: null, signal: null, timedOut: false, error });
    });
    exited.then(() => {
      settle({ ok: false, tail: tailText(), code: exitInfo.code, signal: exitInfo.signal, timedOut: false, error: null });
    });

    timer = setTimeout(async () => {
      if (settled) return;
      settled = true;
      clearInterval(poll);
      await terminate(child, exited);
      resolve({ ok: false, tail: tailText(), code: exitInfo.code, signal: exitInfo.signal, timedOut: true, error: null });
    }, timeoutMs);

    poll = setInterval(async () => {
      if (settled || polling) return;
      polling = true;
      const healthy = await probeHealth(url, fetchFn);
      polling = false;
      if (healthy && !settled) {
        lifecycle.ready = true;
        settle({ ok: true, child, exited, port, url, lifecycle });
      }
    }, HEALTH_INTERVAL_MS);
  });
}

function startError(result, timeoutMs) {
  let message;
  if (result.timedOut) {
    message = t('electron.server.timeout', { ms: timeoutMs });
  } else if (result.error) {
    message = t('electron.server.start_failed', { detail: result.error.message });
  } else {
    message = t('electron.server.exited', { code: result.code ?? result.signal });
  }
  return new ServerStartError(message, result.tail);
}

function makeHandle(ready) {
  const { child, exited, port, url, lifecycle } = ready;
  let stopping = null;
  return {
    port,
    url,
    pid: child.pid,
    stop() {
      if (!stopping) {
        lifecycle.stopRequested = true;
        stopping = terminate(child, exited);
      }
      return stopping;
    },
    onExit(cb) {
      lifecycle.exitListeners.push(cb);
    },
  };
}

/**
 * Starts the Streamlit dashboard on a free port and waits until /_stcore/health answers 200.
 * Up to MAX_ATTEMPTS tries with a new port while the output reports "address already in use".
 * @param {{ python: string[], appRoot: string, dataDir: string | null, timeoutMs?: number,
 *           buildArgsFn?: (appRoot: string, port: number) => string[],
 *           deps?: { findFreePort?: () => Promise<number>, fetch?: typeof fetch } }} opts
 * @returns {Promise<{ port: number, url: string, pid: number | undefined,
 *                     stop: () => Promise<void>, onExit: (cb: Function) => void }>}
 */
async function startServer({
  python,
  appRoot,
  dataDir,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  buildArgsFn = buildArgs,
  deps = {},
}) {
  const findPort = deps.findFreePort ?? (() => findFreePort());
  const fetchFn = deps.fetch ?? fetch;
  const [file, ...prefix] = python;
  let last = null;

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    const port = await findPort();
    const result = await runAttempt({ file, prefix, appRoot, dataDir, buildArgsFn, timeoutMs, fetchFn }, port);
    if (result.ok) return makeHandle(result);
    last = result;
    if (result.timedOut || result.error || !ADDR_IN_USE_RE.test(result.tail)) break;
  }
  throw startError(last, timeoutMs);
}

module.exports = {
  DEFAULT_TIMEOUT_MS,
  STOP_GRACE_MS,
  TAIL_LINES,
  ADDR_IN_USE_RE,
  ServerStartError,
  findFreePort,
  buildArgs,
  buildEnv,
  startServer,
};
