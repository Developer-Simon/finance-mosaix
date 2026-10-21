'use strict';

const { t } = require('./i18n');
const path = require('node:path');
const nodeFs = require('node:fs/promises');
const { findSystemPython } = require('./python-locator');
const { ensureVenv } = require('./venv-manager');

async function defaultExists(p) {
  try {
    await nodeFs.access(p);
    return true;
  } catch {
    return false;
  }
}

/**
 * Path to the bundled Python.
 * @param {string} bundledDir the folder that holds the bundled runtime (e.g. <resources>/python)
 * @param {string} [platform]
 * @returns {string}
 */
function bundledPython(bundledDir, platform = process.platform) {
  return platform === 'win32'
    ? path.win32.join(bundledDir, 'python.exe')
    : path.posix.join(bundledDir, 'bin', 'python3');
}

/**
 * Path to the interpreter of the development venv in the project root.
 * @param {string} appRoot
 * @param {string} [platform]
 * @returns {string}
 */
function devVenvPython(appRoot, platform = process.platform) {
  return platform === 'win32'
    ? path.win32.join(appRoot, '.venv', 'Scripts', 'python.exe')
    : path.posix.join(appRoot, '.venv', 'bin', 'python');
}

class RuntimeUnavailableError extends Error {
  /**
   * @param {{ cmd: string[], reason: string }[]} rejected all rejection reasons
   */
  constructor(rejected) {
    const lines = rejected.map((r) => `  - ${r.cmd.join(' ')}: ${r.reason}`);
    const details = lines.length > 0 ? lines.join('\n') : `  ${t('electron.runtime.none_found')}`;
    super(t('electron.runtime.unavailable', { details, hint: t('electron.runtime.full_hint') }));
    this.name = 'RuntimeUnavailableError';
    this.rejected = rejected;
  }
}

/**
 * Picks the Python interpreter. Order: FINANCE_MOSAIX_PYTHON override, dev venv (not packaged),
 * bundled runtime, system Python with a managed venv in userDataDir.
 * `force` skips the first three steps and reinstalls the system venv.
 *
 * @param {{ isPackaged: boolean, appRoot: string, bundledDir: string, userDataDir: string,
 *           requirementsPath: string, appVersion: string, onProgress?: (m: string) => void,
 *           force?: boolean,
 *           deps?: { find?: Function, ensure?: Function, exists?: Function, env?: object,
 *                    platform?: string } }} opts
 * @returns {Promise<{ python: string[], mode: 'override' | 'dev' | 'bundled' | 'system' }>}
 */
async function resolveRuntime({
  isPackaged,
  appRoot,
  bundledDir,
  userDataDir,
  requirementsPath,
  appVersion,
  onProgress,
  force = false,
  deps = {},
}) {
  const find = deps.find ?? (() => findSystemPython());
  const ensure = deps.ensure ?? ensureVenv;
  const exists = deps.exists ?? defaultExists;
  const env = deps.env ?? process.env;
  const platform = deps.platform ?? process.platform;

  if (!force) {
    if (env.FINANCE_MOSAIX_PYTHON) {
      return { python: [env.FINANCE_MOSAIX_PYTHON], mode: 'override' };
    }

    const devPython = devVenvPython(appRoot, platform);
    if (!isPackaged && (await exists(devPython))) {
      return { python: [devPython], mode: 'dev' };
    }

    const bundled = bundledPython(bundledDir, platform);
    if (await exists(bundled)) {
      return { python: [bundled], mode: 'bundled' };
    }
  }

  const rejected = [];
  const found = await find();
  if (found.python) {
    const venv = await ensure({
      probe: found.python,
      venvDir: path.join(userDataDir, 'venv'),
      requirementsPath,
      appVersion,
      onProgress,
      force,
    });
    return { python: [venv.python], mode: 'system' };
  }
  rejected.push(...(found.rejected ?? []));

  throw new RuntimeUnavailableError(rejected);
}

module.exports = { bundledPython, devVenvPython, resolveRuntime, RuntimeUnavailableError };
