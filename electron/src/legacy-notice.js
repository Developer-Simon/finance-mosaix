'use strict';

const path = require('node:path');
const fs = require('node:fs/promises');

/**
 * Install folder names of the former Windows build (NSIS, electron-builder 24/26 defaults).
 * The old config set no nsis options, so the one-click per-user installer used the package
 * name (`finance-mosaix-electron`) as folder under %LOCALAPPDATA%\Programs. The productName
 * "Finance Mosaix Dashboard" only applies to perMachine or assisted installs, which the old
 * config never enabled, so it is not listed.
 */
const LEGACY_DIR_NAMES = ['finance-mosaix-electron'];

const DB_NAME = 'finance.duckdb';
const STATE_NAME = 'shell-state.json';

/**
 * @param {string} file
 * @returns {Promise<boolean>} true only for an existing regular file; errors count as false.
 */
async function defaultExists(file) {
  try {
    return (await fs.stat(file)).isFile();
  } catch {
    return false;
  }
}

/**
 * Candidate database paths of the former Windows build, in lookup order.
 * @param {Record<string, string | undefined>} env
 * @returns {string[]}
 */
function legacyCandidates(env = {}) {
  const dirs = [];
  for (const name of LEGACY_DIR_NAMES) {
    if (env.LOCALAPPDATA) dirs.push(path.win32.join(env.LOCALAPPDATA, 'Programs', name));
    if (env.ProgramFiles) dirs.push(path.win32.join(env.ProgramFiles, name));
  }
  return dirs.map((dir) => path.win32.join(dir, 'resources', DB_NAME));
}

/**
 * Looks for a database of the former Windows build. Only on win32.
 * @param {{ platform: string, env?: object, exists?: (file: string) => Promise<boolean> }} options
 * @returns {Promise<{ dbPath: string, dir: string } | null>} dir is the former install folder.
 */
async function findLegacyData({ platform, env = {}, exists = defaultExists } = {}) {
  if (platform !== 'win32') return null;
  for (const dbPath of legacyCandidates(env)) {
    if (await exists(dbPath)) {
      return { dbPath, dir: path.win32.dirname(path.win32.dirname(dbPath)) };
    }
  }
  return null;
}

/**
 * Reads shell-state.json. A missing or unreadable file yields {}.
 * @param {string} userDataDir
 * @returns {Promise<object>}
 */
async function readShellState(userDataDir) {
  try {
    const parsed = JSON.parse(await fs.readFile(path.join(userDataDir, STATE_NAME), 'utf8'));
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

/**
 * Writes shell-state.json atomically (temp file, then rename).
 * @param {string} userDataDir
 * @param {object} state
 * @returns {Promise<void>}
 */
async function writeShellState(userDataDir, state) {
  await fs.mkdir(userDataDir, { recursive: true });
  const target = path.join(userDataDir, STATE_NAME);
  const tmp = `${target}.${process.pid}.tmp`;
  try {
    await fs.writeFile(tmp, JSON.stringify(state, null, 2), 'utf8');
    await fs.rename(tmp, target);
  } catch (err) {
    await fs.rm(tmp, { force: true });
    throw err;
  }
}

/**
 * Decides whether the one-time notice about legacy data should be shown.
 * @param {{ userDataDir: string, platform: string, env?: object, exists?: (file: string) => Promise<boolean> }} options
 * @returns {Promise<{ dbPath: string, dir: string } | null>} the legacy data to point to, or null.
 */
async function shouldShowLegacyNotice({ userDataDir, platform, env = {}, exists = defaultExists } = {}) {
  if (await exists(path.join(userDataDir, DB_NAME))) return null;
  const state = await readShellState(userDataDir);
  if (state.legacyNoticeShown) return null;
  return findLegacyData({ platform, env, exists });
}

module.exports = {
  LEGACY_DIR_NAMES,
  legacyCandidates,
  findLegacyData,
  readShellState,
  writeShellState,
  shouldShowLegacyNotice,
};
