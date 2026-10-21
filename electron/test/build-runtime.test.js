'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { targetKey, tarCommand, verifySha256 } = require('../runtime/build-runtime');
const lock = require('../runtime/runtime.lock.json');

test('targetKey maps all four targets and rejects linux-arm64', () => {
  assert.equal(targetKey('linux', 'x64'), 'linux-x64');
  assert.equal(targetKey('darwin', 'arm64'), 'darwin-arm64');
  assert.equal(targetKey('darwin', 'x64'), 'darwin-x64');
  assert.equal(targetKey('win32', 'x64'), 'win32-x64');
  assert.throws(() => targetKey('linux', 'arm64'), /Unsupported platform: linux-arm64/);
});

test('verifySha256 rejects a wrong hash', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'runtime-sha-'));
  try {
    const file = path.join(dir, 'payload.bin');
    fs.writeFileSync(file, 'hello runtime');
    const good = crypto.createHash('sha256').update('hello runtime').digest('hex');
    await verifySha256(file, good);
    await assert.rejects(verifySha256(file, '0'.repeat(64)), /SHA-256 mismatch/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('lock file has entries for all targets with python 3.13.16', () => {
  assert.equal(lock.python, '3.13.16');
  assert.equal(lock.release, '20261013');
  for (const key of ['linux-x64', 'darwin-arm64', 'darwin-x64', 'win32-x64']) {
    const entry = lock.targets[key];
    assert.ok(entry, `missing target ${key}`);
    assert.match(entry.asset, /^cpython-3\.13\.16\+20261013-.*install_only\.tar\.gz$/);
    assert.match(entry.sha256, /^[0-9a-f]{64}$/);
  }
});

test('tarCommand uses the Windows system tar on win32', () => {
  assert.equal(tarCommand('linux', {}), 'tar');
  assert.equal(
    tarCommand('win32', { SystemRoot: 'C:\\Windows' }),
    path.win32.join('C:\\Windows', 'System32', 'tar.exe'),
  );
});
