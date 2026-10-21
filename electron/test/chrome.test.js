'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { TITLEBAR_HEIGHT, chromeColors, contentBackground, barPage, titleBarOptions } = require('../src/chrome');

const PREFIX = 'data:text/html;charset=utf-8,';

function decodePage(url) {
  assert.ok(url.startsWith(PREFIX), 'barPage returns a data:text/html URL');
  return decodeURIComponent(url.slice(PREFIX.length));
}

test('barPage escapes text and contains drag region', () => {
  const html = decodePage(barPage({ title: 'Finance', lang: 'de', text: '<img src=x onerror="a">' }));
  assert.ok(html.includes('-webkit-app-region:drag'));
  assert.ok(html.includes('&lt;img src=x onerror=&quot;a&quot;&gt;'));
  assert.ok(!html.includes('<img src=x'));
  assert.ok(html.includes('prefers-color-scheme: dark'));
});

test('barPage shows the logo in the title bar and keeps the window title', () => {
  const html = decodePage(barPage({ title: 'Finance Mosaix' }));
  assert.match(html, /<header class="bar"[^>]*><svg [^>]*aria-label="finance mosaix"/);
  assert.ok(html.includes('<title>Finance Mosaix</title>'));
});

test('titleBarOptions darwin uses traffic lights', () => {
  assert.deepEqual(titleBarOptions('darwin', false), {
    titleBarStyle: 'hidden',
    trafficLightPosition: { x: 16, y: 11 },
  });
});

test('titleBarOptions elsewhere uses a colour overlay of the title bar height', () => {
  assert.deepEqual(titleBarOptions('win32', true), {
    titleBarStyle: 'hidden',
    titleBarOverlay: { color: '#262730', symbolColor: '#fafafa', height: TITLEBAR_HEIGHT },
  });
});

test('chrome colours and content background match the spec', () => {
  assert.equal(TITLEBAR_HEIGHT, 36);
  assert.deepEqual(chromeColors(false), { color: '#f0f2f6', symbolColor: '#31333f' });
  assert.deepEqual(chromeColors(true), { color: '#262730', symbolColor: '#fafafa' });
  assert.equal(contentBackground(false), '#ffffff');
  assert.equal(contentBackground(true), '#0e1117');
});
