'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { resolveLanguage, init, t, currentLanguage } = require('../src/i18n');

const SRC_I18N = path.join(__dirname, '..', 'src', 'i18n');

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'fm-i18n-'));
}

test('resolveLanguage uses the base subtag of the first preferred language', () => {
  const av = ['en', 'de'];
  assert.equal(resolveLanguage(['de-CH'], av), 'de');
  assert.equal(resolveLanguage(['de_AT', 'en-US'], av), 'de');
  assert.equal(resolveLanguage(['fr-FR', 'de-DE'], av), 'en');
  assert.equal(resolveLanguage([], av), 'en');
});

test('t fills in placeholders, loads the resolved language and falls back to en', () => {
  const dir = tmpDir();
  fs.writeFileSync(path.join(dir, 'en.json'), JSON.stringify({ a: 'A {x}', only_en: 'Only English' }));
  fs.writeFileSync(path.join(dir, 'de.json'), JSON.stringify({ a: 'Ä {x}' }));
  init({ dir, preferred: ['de-DE'] });
  assert.equal(currentLanguage(), 'de');
  assert.equal(t('a', { x: '{x}' }), 'Ä {x}'); // values are not expanded again
  assert.equal(t('only_en'), 'Only English');
  assert.equal(t('a'), 'Ä {x}'); // unknown placeholder stays
  assert.equal(t('unknown_key'), 'unknown_key');
  init({ dir, preferred: ['fr'] });
  assert.equal(currentLanguage(), 'en');
});

test('t falls back to en and returns the key when missing', () => {
  init({ dir: SRC_I18N, preferred: ['de'] });
  assert.equal(t('electron.dialog.ok'), 'OK');
  assert.equal(t('electron.does.not.exist'), 'electron.does.not.exist');
  init({ dir: SRC_I18N, preferred: [] });
  assert.equal(t('electron.menu.tools'), 'Tools');
});

test('de.json and en.json have identical key sets', () => {
  const en = JSON.parse(fs.readFileSync(path.join(SRC_I18N, 'en.json'), 'utf8'));
  const de = JSON.parse(fs.readFileSync(path.join(SRC_I18N, 'de.json'), 'utf8'));
  assert.deepEqual(Object.keys(de).sort(), Object.keys(en).sort());
});
