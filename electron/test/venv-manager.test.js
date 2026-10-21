'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs/promises');
const { t: translate } = require('../src/i18n');
const { STAMP_NAME, venvPython, requirementsHash, ensureVenv } = require('../src/venv-manager');

const PLATFORM = 'linux';
const PROBE = { cmd: ['python3'], version: [3, 12, 4] };
const APP_VERSION = '1.0.0';
const REQUIREMENTS_TEXT = 'numpy==2.1.0\n';
const PIP_ARGS = (requirementsPath) => [
  '-m',
  'pip',
  'install',
  '--disable-pip-version-check',
  '--no-input',
  '-r',
  requirementsPath,
];

async function setup(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'venv-manager-test-'));
  t.after(() => fs.rm(root, { recursive: true, force: true }));
  const requirementsPath = path.join(root, 'requirements.txt');
  await fs.writeFile(requirementsPath, REQUIREMENTS_TEXT, 'utf8');
  return { venvDir: path.join(root, 'venv'), requirementsPath };
}

// Fake runner: `-m venv` creates the interpreter file in the venv folder, the pip
// call goes through runLines and can emit lines or fail as configured.
function makeDeps({ pipFails = false, pipLines = [] } = {}) {
  const calls = [];
  const run = async (file, args) => {
    calls.push({ kind: 'run', file, args });
    const dir = args[args.length - 1];
    await fs.mkdir(path.dirname(venvPython(dir, PLATFORM)), { recursive: true });
    await fs.writeFile(venvPython(dir, PLATFORM), '');
    return { stdout: '', stderr: '' };
  };
  const runLines = async (file, args, opts) => {
    calls.push({ kind: 'runLines', file, args, timeout: opts.timeout });
    for (const line of pipLines) opts.onLine(line);
    if (pipFails) throw new Error('pip failed');
  };
  return { deps: { run, runLines, platform: PLATFORM }, calls };
}

async function readStamp(venvDir) {
  return JSON.parse(await fs.readFile(path.join(venvDir, STAMP_NAME), 'utf8'));
}

async function writeStamp(venvDir, stamp) {
  await fs.mkdir(venvDir, { recursive: true });
  await fs.writeFile(path.join(venvDir, STAMP_NAME), JSON.stringify(stamp));
}

async function makeInterpreter(venvDir) {
  await fs.mkdir(path.dirname(venvPython(venvDir, PLATFORM)), { recursive: true });
  await fs.writeFile(venvPython(venvDir, PLATFORM), '');
}

async function exists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

test('venvPython on win32 uses Scripts\\python.exe', () => {
  assert.equal(venvPython('/x/venv', 'linux'), path.posix.join('/x/venv', 'bin', 'python'));
  assert.equal(venvPython('C:\\v', 'win32'), path.win32.join('C:\\v', 'Scripts', 'python.exe'));
});

test('ensureVenv creates venv and installs requirements on first run', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  const { deps, calls } = makeDeps();

  const result = await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: APP_VERSION, deps });

  assert.deepEqual(result, { python: venvPython(venvDir, PLATFORM), installed: true });
  assert.deepEqual(
    calls.map((c) => c.kind),
    ['run', 'runLines'],
  );
  assert.equal(calls[0].file, 'python3');
  assert.deepEqual(calls[0].args, ['-m', 'venv', venvDir]);
  assert.equal(calls[1].file, venvPython(venvDir, PLATFORM));
  assert.deepEqual(calls[1].args, PIP_ARGS(requirementsPath));
  assert.deepEqual(await readStamp(venvDir), {
    python: '3.12',
    appVersion: APP_VERSION,
    requirementsHash: requirementsHash(REQUIREMENTS_TEXT),
    complete: true,
  });
});

test('ensureVenv skips install when stamp matches', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  const { deps, calls } = makeDeps();
  await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: APP_VERSION, deps });
  calls.length = 0;

  const result = await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: APP_VERSION, deps });

  assert.deepEqual(result, { python: venvPython(venvDir, PLATFORM), installed: false });
  assert.equal(calls.length, 0);
});

test('ensureVenv reinstalls when the stamp is incomplete', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  await makeInterpreter(venvDir);
  await writeStamp(venvDir, {
    python: '3.12',
    appVersion: APP_VERSION,
    requirementsHash: requirementsHash(REQUIREMENTS_TEXT),
    complete: false,
  });
  const { deps, calls } = makeDeps();

  const result = await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: APP_VERSION, deps });

  assert.deepEqual(result, { python: venvPython(venvDir, PLATFORM), installed: true });
  assert.deepEqual(calls.map((c) => c.kind), ['runLines']);
  assert.equal((await readStamp(venvDir)).complete, true);
});

test('ensureVenv reinstalls when appVersion or requirements hash changes', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  const { deps, calls } = makeDeps();
  await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: APP_VERSION, deps });

  calls.length = 0;
  const byVersion = await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: '1.0.1', deps });
  assert.equal(byVersion.installed, true);
  assert.deepEqual(calls.map((c) => c.kind), ['runLines']);

  calls.length = 0;
  await fs.writeFile(requirementsPath, 'numpy==2.2.0\n', 'utf8');
  const byHash = await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: '1.0.1', deps });
  assert.equal(byHash.installed, true);
  assert.deepEqual(calls.map((c) => c.kind), ['runLines']);
  assert.equal((await readStamp(venvDir)).requirementsHash, requirementsHash('numpy==2.2.0\n'));
});

test('ensureVenv recreates the venv when the python minor version changes', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  await makeInterpreter(venvDir);
  await fs.writeFile(path.join(venvDir, 'stale.txt'), 'old');
  await writeStamp(venvDir, {
    python: '3.11',
    appVersion: APP_VERSION,
    requirementsHash: requirementsHash(REQUIREMENTS_TEXT),
    complete: true,
  });
  const { deps, calls } = makeDeps();

  const result = await ensureVenv({
    probe: { cmd: ['python3'], version: [3, 13, 0] },
    venvDir,
    requirementsPath,
    appVersion: APP_VERSION,
    deps,
  });

  assert.equal(result.installed, true);
  assert.equal(await exists(path.join(venvDir, 'stale.txt')), false);
  assert.deepEqual(calls[0].args, ['-m', 'venv', venvDir]);
  assert.equal((await readStamp(venvDir)).python, '3.13');
});

test('ensureVenv with force reinstalls', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  const { deps } = makeDeps();
  await ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: APP_VERSION, deps });
  const { deps: forced, calls } = makeDeps();

  const result = await ensureVenv({
    probe: PROBE,
    venvDir,
    requirementsPath,
    appVersion: APP_VERSION,
    force: true,
    deps: forced,
  });

  assert.equal(result.installed, true);
  assert.deepEqual(calls.map((c) => c.kind), ['runLines']);
});

test('ensureVenv rejects and leaves complete=false when pip fails', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  const { deps } = makeDeps({ pipFails: true });

  await assert.rejects(
    ensureVenv({ probe: PROBE, venvDir, requirementsPath, appVersion: APP_VERSION, deps }),
    /pip failed/,
  );
  assert.equal((await readStamp(venvDir)).complete, false);
});

test('progress lines are forwarded', async (t) => {
  const { venvDir, requirementsPath } = await setup(t);
  const { deps } = makeDeps({
    pipLines: [
      'Collecting numpy==2.1.0',
      'Requirement already satisfied: six',
      'Downloading numpy-2.1.0.whl',
      'Installing collected packages: numpy',
    ],
  });
  const messages = [];

  await ensureVenv({
    probe: PROBE,
    venvDir,
    requirementsPath,
    appVersion: APP_VERSION,
    deps,
    onProgress: (m) => messages.push(m),
  });

  const install = translate('electron.loading.install_deps');
  assert.deepEqual(messages, [
    translate('electron.loading.create_venv'),
    `${install}\nCollecting numpy==2.1.0`,
    `${install}\nDownloading numpy-2.1.0.whl`,
    `${install}\nInstalling collected packages: numpy`,
  ]);
});
