'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs/promises');
const {
  LEGACY_DIR_NAMES,
  legacyCandidates,
  findLegacyData,
  readShellState,
  writeShellState,
  shouldShowLegacyNotice,
} = require('../src/legacy-notice');

const ENV = {
  LOCALAPPDATA: 'C:\\Users\\tester\\AppData\\Local',
  ProgramFiles: 'C:\\Program Files',
};
const NAME = LEGACY_DIR_NAMES[0];
const LEGACY_DB = path.win32.join(ENV.LOCALAPPDATA, 'Programs', NAME, 'resources', 'finance.duckdb');

async function tempDir(t) {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'legacy-notice-test-'));
  t.after(() => fs.rm(dir, { recursive: true, force: true }));
  return dir;
}

test('findLegacyData returns null off win32', async () => {
  const result = await findLegacyData({ platform: 'linux', env: ENV, exists: async () => true });
  assert.equal(result, null);
});

test('findLegacyData finds db under LOCALAPPDATA Programs', async () => {
  const seen = [];
  const exists = async (file) => {
    seen.push(file);
    return file === LEGACY_DB;
  };
  const result = await findLegacyData({ platform: 'win32', env: ENV, exists });
  assert.deepEqual(result, {
    dbPath: LEGACY_DB,
    dir: path.win32.join(ENV.LOCALAPPDATA, 'Programs', NAME),
  });
  assert.equal(seen[0], LEGACY_DB);
});

test('legacyCandidates covers LOCALAPPDATA and ProgramFiles per name', () => {
  assert.deepEqual(legacyCandidates(ENV), [
    LEGACY_DB,
    path.win32.join(ENV.ProgramFiles, NAME, 'resources', 'finance.duckdb'),
  ]);
});

test('readShellState returns {} for a missing or broken file', async (t) => {
  const dir = await tempDir(t);
  assert.deepEqual(await readShellState(dir), {});
  await fs.writeFile(path.join(dir, 'shell-state.json'), '{ broken', 'utf8');
  assert.deepEqual(await readShellState(dir), {});
});

test('shouldShowLegacyNotice null once shown or when userData db exists', async (t) => {
  const dir = await tempDir(t);
  const existsLegacy = async (file) => file === LEGACY_DB;
  const found = { dbPath: LEGACY_DB, dir: path.win32.join(ENV.LOCALAPPDATA, 'Programs', NAME) };

  // Legacy data present and nothing shown yet: notice is due.
  assert.deepEqual(
    await shouldShowLegacyNotice({ userDataDir: dir, platform: 'win32', env: ENV, exists: existsLegacy }),
    found,
  );

  // Already shown once.
  await writeShellState(dir, { legacyNoticeShown: true });
  assert.equal(
    await shouldShowLegacyNotice({ userDataDir: dir, platform: 'win32', env: ENV, exists: existsLegacy }),
    null,
  );

  // Current userData database exists: no notice.
  const dir2 = await tempDir(t);
  const existsBoth = async (file) => file === LEGACY_DB || file === path.join(dir2, 'finance.duckdb');
  assert.equal(
    await shouldShowLegacyNotice({ userDataDir: dir2, platform: 'win32', env: ENV, exists: existsBoth }),
    null,
  );
});

test('writeShellState round-trips through readShellState', async (t) => {
  const dir = await tempDir(t);
  await writeShellState(dir, { legacyNoticeShown: true });
  assert.deepEqual(await readShellState(dir), { legacyNoticeShown: true });
});
