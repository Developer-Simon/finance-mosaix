'use strict';

const { t } = require('./i18n');
const { execFile } = require('node:child_process');
const { promisify } = require('node:util');

const MIN_PYTHON = [3, 11];
const PROBE_TIMEOUT_MS = 10000;

// One-liner: prints the version and whether ensurepip/venv are available, as JSON.
const PROBE_SCRIPT =
  'import json,sys,importlib.util as u;' +
  'print(json.dumps({"v":list(sys.version_info[:3]),' +
  '"venv":all(u.find_spec(m) is not None for m in ("ensurepip","venv"))}))';

const execFileAsync = promisify(execFile);

/** @type {(file: string, args: string[], opts: { timeout: number }) => Promise<{ stdout: string, stderr: string }>} */
const defaultRun = (file, args, opts) => execFileAsync(file, args, { ...opts, windowsHide: true });

function isAtLeast(version, min) {
  for (let i = 0; i < min.length; i++) {
    if (version[i] !== min[i]) return version[i] > min[i];
  }
  return true;
}

/**
 * Checks whether `cmd` is a usable Python (>= MIN_PYTHON with venv/ensurepip).
 * @param {string[]} cmd e.g. ["python3"] or ["py", "-3"]
 * @param {Function} [run]
 * @returns {Promise<{ ok: true, cmd: string[], version: number[] } | { ok: false, cmd: string[], reason: string }>}
 */
async function probePython(cmd, run = defaultRun) {
  const [file, ...prefix] = cmd;
  const fail = (reason) => ({ ok: false, cmd, reason });

  let stdout;
  try {
    ({ stdout } = await run(file, [...prefix, '-c', PROBE_SCRIPT], { timeout: PROBE_TIMEOUT_MS }));
  } catch (err) {
    if (err && err.killed) return fail(t('electron.python.timeout'));
    if (err && err.code === 'ENOENT') return fail(t('electron.python.not_found'));
    return fail(t('electron.python.start_failed', { detail: err && err.message ? err.message : String(err) }));
  }

  let info;
  try {
    info = JSON.parse(String(stdout).trim());
  } catch {
    return fail(t('electron.python.bad_output'));
  }

  const version = Array.isArray(info && info.v) ? info.v : null;
  if (!version || version.length < 3) return fail(t('electron.python.bad_version'));
  if (!isAtLeast(version, MIN_PYTHON)) {
    return fail(t('electron.python.too_old', { version: version.join('.'), min: MIN_PYTHON.join('.') }));
  }
  if (!info.venv) return fail(t('electron.python.no_venv'));
  return { ok: true, cmd, version };
}

/**
 * Finds the first suitable system Python for the platform.
 * @param {string} [platform]
 * @param {Function} [run]
 * @returns {Promise<{ python: { cmd: string[], version: number[] } | null, rejected: { cmd: string[], reason: string }[] }>}
 */
async function findSystemPython(platform = process.platform, run = defaultRun) {
  const candidates =
    platform === 'win32'
      ? [['py', '-3'], ['python'], ['python3']]
      : [['python3'], ['python']];

  const rejected = [];
  for (const cmd of candidates) {
    const result = await probePython(cmd, run);
    if (result.ok) {
      return { python: { cmd: result.cmd, version: result.version }, rejected };
    }
    rejected.push({ cmd, reason: result.reason });
  }
  return { python: null, rejected };
}

module.exports = { MIN_PYTHON, probePython, findSystemPython };
