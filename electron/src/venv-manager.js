'use strict';

const { t } = require('./i18n');
const { execFile, spawn } = require('node:child_process');
const { promisify } = require('node:util');
const { createHash } = require('node:crypto');
const readline = require('node:readline');
const path = require('node:path');
const nodeFs = require('node:fs/promises');

const STAMP_NAME = 'finance-mosaix-stamp.json';
const VENV_TIMEOUT_MS = 5 * 60 * 1000;
const PIP_TIMEOUT_MS = 15 * 60 * 1000;
const TAIL_LINES = 20;
const PROGRESS_PREFIXES = ['Collecting ', 'Downloading ', 'Installing collected packages'];

const execFileAsync = promisify(execFile);

/** @type {(file: string, args: string[], opts: { timeout: number }) => Promise<{ stdout: string, stderr: string }>} */
const defaultRun = (file, args, opts) => execFileAsync(file, args, { ...opts, windowsHide: true });

/**
 * Runs a process and reports each stdout/stderr line. Rejects on a non-zero exit code;
 * the message then carries the last lines of output.
 * @param {string} file
 * @param {string[]} args
 * @param {{ timeout: number, onLine?: (line: string) => void }} opts
 * @returns {Promise<void>}
 */
function defaultRunLines(file, args, { timeout, onLine } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(file, args, { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    const tail = [];
    let timer = null;
    let settled = false;

    const finish = (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (err) reject(err);
      else resolve();
    };

    const handle = (line) => {
      tail.push(line);
      if (tail.length > TAIL_LINES) tail.shift();
      if (onLine) onLine(line);
    };

    for (const stream of [child.stdout, child.stderr]) {
      readline.createInterface({ input: stream }).on('line', handle);
    }

    if (timeout) {
      timer = setTimeout(() => {
        child.kill();
        finish(new Error(`${file} timed out after ${timeout} ms`));
      }, timeout);
    }

    child.on('error', finish);
    child.on('close', (code) => {
      if (code === 0) finish();
      else finish(new Error(`${file} exited with code ${code}\n${tail.join('\n')}`));
    });
  });
}

/**
 * Path to the interpreter in a venv.
 * @param {string} venvDir
 * @param {string} [platform]
 */
function venvPython(venvDir, platform = process.platform) {
  return platform === 'win32'
    ? path.win32.join(venvDir, 'Scripts', 'python.exe')
    : path.posix.join(venvDir, 'bin', 'python');
}

/**
 * @param {string} text
 * @returns {string} sha256 as hex
 */
function requirementsHash(text) {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

async function readStamp(fs, stampPath) {
  try {
    const data = JSON.parse(await fs.readFile(stampPath, 'utf8'));
    return data && typeof data === 'object' ? data : null;
  } catch {
    return null;
  }
}

// Writes through a temp file, so an abort doesn't leave half a stamp behind.
async function writeStamp(fs, stampPath, stamp) {
  const tmp = `${stampPath}.tmp`;
  await fs.writeFile(tmp, JSON.stringify(stamp, null, 2) + '\n', 'utf8');
  await fs.rename(tmp, stampPath);
}

async function exists(fs, p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

/**
 * Makes sure a venv in `venvDir` exists and has the requirements installed.
 * Reinstalls when forced, when the stamp is missing or incomplete, when appVersion
 * or the requirements hash changed, or when the interpreter is gone. A different
 * Python minor version recreates the venv folder.
 *
 * @param {{ probe: { cmd: string[], version: number[] }, venvDir: string,
 *           requirementsPath: string, appVersion: string,
 *           onProgress?: (msg: string) => void, force?: boolean,
 *           deps?: { run?: Function, runLines?: Function, fs?: typeof import("node:fs/promises"),
 *                    platform?: string } }} opts
 * @returns {Promise<{ python: string, installed: boolean }>}
 */
async function ensureVenv({
  probe,
  venvDir,
  requirementsPath,
  appVersion,
  onProgress,
  force = false,
  deps = {},
}) {
  const { run = defaultRun, runLines = defaultRunLines, fs = nodeFs, platform = process.platform } = deps;
  const python = venvPython(venvDir, platform);
  const stampPath = path.join(venvDir, STAMP_NAME);
  const wantedPython = `${probe.version[0]}.${probe.version[1]}`;
  const hash = requirementsHash(await fs.readFile(requirementsPath, 'utf8'));

  const stamp = await readStamp(fs, stampPath);
  const upToDate =
    stamp !== null &&
    stamp.complete === true &&
    stamp.python === wantedPython &&
    stamp.appVersion === appVersion &&
    stamp.requirementsHash === hash &&
    (await exists(fs, python));

  if (!force && upToDate) return { python, installed: false };

  if (stamp !== null && stamp.python !== wantedPython) {
    await fs.rm(venvDir, { recursive: true, force: true });
  }

  // complete stays false until the install has finished; that way an abort is recognised.
  await fs.mkdir(venvDir, { recursive: true });
  await writeStamp(fs, stampPath, {
    python: wantedPython,
    appVersion,
    requirementsHash: hash,
    complete: false,
  });

  if (!(await exists(fs, python))) {
    onProgress?.(t('electron.loading.create_venv'));
    await run(probe.cmd[0], [...probe.cmd.slice(1), '-m', 'venv', venvDir], {
      timeout: VENV_TIMEOUT_MS,
    });
    if (!(await exists(fs, python))) {
      throw new Error(t('electron.venv.no_interpreter', { python }));
    }
  }

  await runLines(
    python,
    ['-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', '-r', requirementsPath],
    {
      timeout: PIP_TIMEOUT_MS,
      onLine: (line) => {
        if (onProgress && PROGRESS_PREFIXES.some((prefix) => line.startsWith(prefix))) {
          onProgress(t('electron.loading.install_deps') + '\n' + line);
        }
      },
    },
  );

  await writeStamp(fs, stampPath, {
    python: wantedPython,
    appVersion,
    requirementsHash: hash,
    complete: true,
  });
  return { python, installed: true };
}

module.exports = { STAMP_NAME, venvPython, requirementsHash, ensureVenv };
