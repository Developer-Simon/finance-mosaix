'use strict';

const fs = require('node:fs');
const path = require('node:path');

const PLACEHOLDER = /\{(\w+)\}/g;
const DEFAULT_DIR = path.resolve(__dirname, 'i18n');
const LANGUAGES = ['de', 'en'];

let lang = 'en';
let messages = {};
let fallback = null;

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return {};
  }
}

/**
 * Same rule as mailviewer.i18n.resolve_language: the base subtag of the first preferred
 * system language if it is available, otherwise English.
 * @param {string[]} preferred e.g. ["de-CH", "en-US"]
 * @param {string[]} available e.g. ["de", "en"]
 * @returns {string}
 */
function resolveLanguage(preferred, available) {
  const first = Array.isArray(preferred) && typeof preferred[0] === 'string' ? preferred[0] : '';
  const base = first.toLowerCase().split(/[-_]/)[0];
  return available.includes(base) ? base : 'en';
}

function format(text, params) {
  return String(text).replace(PLACEHOLDER, (whole, name) =>
    Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : whole,
  );
}

/**
 * Loads en.json and the resolved language file.
 * @param {{ dir?: string, preferred?: string[] }} [options]
 */
function init({ dir = DEFAULT_DIR, preferred = [] } = {}) {
  lang = resolveLanguage(preferred, LANGUAGES);
  fallback = readJson(path.join(dir, 'en.json'));
  messages = lang === 'en' ? fallback : readJson(path.join(dir, `${lang}.json`));
}

function ensureLoaded() {
  if (fallback === null) init();
}

/**
 * Returns the text for `key` with `{name}` placeholders filled in. A missing key yields the key itself.
 * @param {string} key
 * @param {object} [params]
 * @returns {string}
 */
function t(key, params = {}) {
  ensureLoaded();
  if (Object.prototype.hasOwnProperty.call(messages, key)) return format(messages[key], params);
  if (Object.prototype.hasOwnProperty.call(fallback, key)) return format(fallback[key], params);
  return key;
}

/** @returns {'de' | 'en'} */
function currentLanguage() {
  ensureLoaded();
  return lang;
}

module.exports = { init, t, currentLanguage, resolveLanguage };
