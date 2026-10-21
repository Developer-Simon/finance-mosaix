'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { init } = require('../src/i18n');
const {
  bundledPython,
  devVenvPython,
  resolveRuntime,
  RuntimeUnavailableError,
} = require('../src/resolve-runtime');

init({ preferred: ['en'] });

const APP_ROOT = '/home/u/dev/finance-mosaix';
const BUNDLED_DIR = '/opt/app/resources/python';
const USER_DATA = '/home/u/.config/finance-mosaix';
const REQ = '/opt/app/requirements.txt';
const SYS_PROBE = { cmd: ['python3'], version: [3, 12, 1] };
const DEV_PY = path.posix.join(APP_ROOT, '.venv', 'bin', 'python');
const BUNDLED = path.posix.join(BUNDLED_DIR, 'bin', 'python3');
const VENV_PY = path.posix.join(USER_DATA, 'venv', 'bin', 'python');

// Fakes: no real Python, no filesystem access.
function fakes({ found = SYS_PROBE, existing = [], ensureError = null } = {}) {
  const calls = { find: 0, ensure: [], exists: [] };
  const deps = {
    platform: 'linux',
    env: {},
    find: async () => {
      calls.find++;
      return {
        python: found ? { cmd: found.cmd, version: found.version } : null,
        rejected: found ? [] : [{ cmd: ['python3'], reason: 'not found' }],
      };
    },
    ensure: async (opts) => {
      calls.ensure.push(opts);
      if (ensureError) throw ensureError;
      return { python: VENV_PY, installed: true };
    },
    exists: async (p) => {
      calls.exists.push(p);
      return existing.includes(p);
    },
  };
  return { deps, calls };
}

const base = { isPackaged: false, appRoot: APP_ROOT, bundledDir: BUNDLED_DIR, userDataDir: USER_DATA, requirementsPath: REQ, appVersion: '0.2.0' };
const resolve = (deps, extra = {}) => resolveRuntime({ ...base, deps, ...extra });

test('bundledPython and devVenvPython return the path per platform', () => {
  assert.equal(bundledPython(BUNDLED_DIR, 'linux'), path.posix.join(BUNDLED_DIR, 'bin', 'python3'));
  assert.equal(bundledPython('C:\\app\\resources\\python', 'win32'), path.win32.join('C:\\app\\resources\\python', 'python.exe'));
  assert.equal(devVenvPython(APP_ROOT, 'linux'), DEV_PY);
  assert.equal(devVenvPython('C:\\dev\\fm', 'win32'), path.win32.join('C:\\dev\\fm', '.venv', 'Scripts', 'python.exe'));
});

test('override wins over everything', async () => {
  const { deps, calls } = fakes({ existing: [DEV_PY, BUNDLED] });
  deps.env = { FINANCE_MOSAIX_PYTHON: '/custom/python' };
  assert.deepEqual(await resolve(deps), { python: ['/custom/python'], mode: 'override' });
  assert.equal(calls.find, 0);
  assert.equal(calls.ensure.length, 0);
});

test('dev venv is used only when not packaged', async () => {
  const { deps } = fakes({ existing: [DEV_PY, BUNDLED] });
  assert.deepEqual(await resolve(deps), { python: [DEV_PY], mode: 'dev' });

  const packaged = fakes({ existing: [DEV_PY, BUNDLED] });
  assert.deepEqual(await resolve(packaged.deps, { isPackaged: true }), { python: [BUNDLED], mode: 'bundled' });
  assert.ok(!packaged.calls.exists.includes(DEV_PY), 'dev venv must not even be probed when packaged');
});

test('bundled wins over system python', async () => {
  const { deps, calls } = fakes({ existing: [BUNDLED] });
  assert.deepEqual(await resolve(deps), { python: [BUNDLED], mode: 'bundled' });
  assert.equal(calls.find, 0, 'find must not be called');
  assert.equal(calls.ensure.length, 0);
});

test('falls back to system venv when nothing is bundled', async () => {
  const { deps, calls } = fakes();
  assert.deepEqual(await resolve(deps), { python: [VENV_PY], mode: 'system' });
  assert.equal(calls.ensure.length, 1);
  assert.equal(calls.ensure[0].venvDir, path.join(USER_DATA, 'venv'));
  assert.deepEqual(calls.ensure[0].probe, SYS_PROBE);
  assert.equal(calls.ensure[0].requirementsPath, REQ);
  assert.equal(calls.ensure[0].appVersion, '0.2.0');
  assert.equal(calls.ensure[0].force, false);
});

test('force skips steps 1-3 and passes force to ensure', async () => {
  const { deps, calls } = fakes({ existing: [DEV_PY, BUNDLED] });
  deps.env = { FINANCE_MOSAIX_PYTHON: '/custom/python' };
  assert.deepEqual(await resolve(deps, { force: true }), { python: [VENV_PY], mode: 'system' });
  assert.equal(calls.exists.length, 0);
  assert.equal(calls.ensure[0].force, true);
});

test('throws RuntimeUnavailableError listing rejected candidates', async () => {
  const { deps } = fakes({ found: null });
  await assert.rejects(resolve(deps), (err) => {
    assert.ok(err instanceof RuntimeUnavailableError);
    assert.equal(err.name, 'RuntimeUnavailableError');
    assert.deepEqual(err.rejected, [{ cmd: ['python3'], reason: 'not found' }]);
    assert.match(err.message, /python3: not found/);
    assert.match(err.message, /3\.11/);
    return true;
  });
});

test('win32 bundled path is python.exe in bundledDir', async () => {
  const winDir = 'C:\\app\\resources\\python';
  const winBundled = path.win32.join(winDir, 'python.exe');
  const { deps } = fakes({ existing: [winBundled] });
  deps.platform = 'win32';
  assert.deepEqual(await resolve(deps, { bundledDir: winDir }), { python: [winBundled], mode: 'bundled' });
});
