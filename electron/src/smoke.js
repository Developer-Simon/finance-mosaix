'use strict';

const http = require('node:http');

const DEFAULT_TIMEOUT_MS = 10 * 1000;

/**
 * GET with a timeout. Resolves to { status, body }, or null on network error or timeout.
 * @param {string} url
 * @param {number} timeoutMs
 * @returns {Promise<{ status: number, body: string } | null>}
 */
function get(url, timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    const done = (value) => {
      if (!settled) {
        settled = true;
        resolve(value);
      }
    };

    const req = http.get(url, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        body += chunk;
      });
      res.on('end', () => done({ status: res.statusCode, body }));
      res.on('error', () => done(null));
    });
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      done(null);
    });
    req.on('error', () => done(null));
  });
}

/**
 * Checks that the Streamlit server is up: GET <url>_stcore/health answers 200, and GET <url>
 * answers 200 with an HTML document containing <title. Never throws.
 * @param {string} url server base URL, e.g. "http://127.0.0.1:8501/"
 * @param {{ timeoutMs?: number }} [options] timeout per request
 * @returns {Promise<boolean>}
 */
async function runSmoke(url, { timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const base = url.endsWith('/') ? url : `${url}/`;
  const health = await get(`${base}_stcore/health`, timeoutMs);
  if (!health || health.status !== 200) return false;
  const page = await get(base, timeoutMs);
  return Boolean(page && page.status === 200 && /<title/.test(page.body));
}

module.exports = { runSmoke };
