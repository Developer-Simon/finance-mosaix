'use strict';

const path = require('node:path');
const { app, BrowserWindow, Menu, WebContentsView, dialog, nativeTheme, shell } = require('electron');
const { resolveRuntime } = require('./resolve-runtime');
const { startServer, ServerStartError } = require('./server-process');
const { runSmoke } = require('./smoke');
const i18n = require('./i18n');
const { t } = i18n;
const { TITLEBAR_HEIGHT, barPage, chromeColors, contentBackground, titleBarOptions } = require('./chrome');
const { shouldShowLegacyNotice, readShellState, writeShellState } = require('./legacy-notice');

const WEB_PREFERENCES = { contextIsolation: true, nodeIntegration: false, sandbox: true };
const TITLE = 'Finance Mosaix';
const ICON_PATH = path.join(__dirname, '..', 'assets', 'icon.png');
/** `--smoke`: start the server, check GET /, quit without dialogs with exit code 0 or 1. */
const SMOKE = process.argv.includes('--smoke');

// Set the name before the first start: matches the packages' productName.
app.setName(TITLE);
// In the Flatpak the Wayland app_id must match the Flatpak ID, otherwise the shell doesn't match the window
// to its desktop file (icon, name).
if (process.env.FLATPAK_ID) app.setDesktopName(`${process.env.FLATPAK_ID}.desktop`);

function getAppRoot() {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, '..', '..');
}

function getRequirementsPath() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'requirements.txt')
    : path.join(__dirname, '..', 'build', 'requirements.txt');
}

/** Packaged: the database lives in userData. Development: null, the repo root is used (or the inherited env var). */
function getDataDir() {
  return app.isPackaged ? app.getPath('userData') : null;
}

function runtimeOptions() {
  return {
    isPackaged: app.isPackaged,
    appRoot: getAppRoot(),
    bundledDir: app.isPackaged
      ? path.join(process.resourcesPath, 'python')
      : path.join(__dirname, '..', 'build', 'python'),
    userDataDir: app.getPath('userData'),
    requirementsPath: getRequirementsPath(),
    appVersion: app.getVersion(),
    onProgress: showLoading,
  };
}

function messageOf(err) {
  return err && err.message ? err.message : String(err);
}

/** Error text for the dialog; for a ServerStartError including the server's output. */
function describeError(err) {
  if (err instanceof ServerStartError && err.stderrTail) {
    return `${err.message}\n\n${t('electron.error.server_output')}\n${err.stderrTail}`;
  }
  return messageOf(err);
}

/** Updates the title bar overlay and window background of open windows when the system theme changes. */
function applyChromeColors() {
  const dark = nativeTheme.shouldUseDarkColors;
  for (const win of [mainWindow, loadingWindow]) {
    if (!win || win.isDestroyed()) continue;
    win.setBackgroundColor(contentBackground(dark));
    if (process.platform === 'darwin') continue;
    try {
      win.setTitleBarOverlay({ ...chromeColors(dark), height: TITLEBAR_HEIGHT });
    } catch {
      // No overlay on this platform/version; the bar then keeps its colours.
    }
  }
  if (mainView && !mainView.webContents.isDestroyed()) mainView.setBackgroundColor(contentBackground(dark));
}

/** @type {BrowserWindow | null} */
let loadingWindow = null;
/** @type {BrowserWindow | null} */
let mainWindow = null;
/** Streamlit view below the title bar of mainWindow. */
/** @type {WebContentsView | null} */
let mainView = null;
/** @type {{ url: string, port: number, pid: number | undefined, stop: () => Promise<void>, onExit: (cb: Function) => void } | null} */
let server = null;
let serverUrl = null;
/** @type {{ python: string[], mode: string } | null} */
let runtime = null;
let quitting = false;
/** Running start/restart operation; onBeforeQuit waits for it. */
let backendOp = null;

function showLoading(text) {
  if (quitting) return;
  const dark = nativeTheme.shouldUseDarkColors;
  if (!loadingWindow) {
    loadingWindow = new BrowserWindow({
      width: 420,
      height: 200,
      resizable: false,
      autoHideMenuBar: true,
      title: TITLE,
      icon: ICON_PATH,
      backgroundColor: contentBackground(dark),
      ...titleBarOptions(process.platform, dark),
      webPreferences: WEB_PREFERENCES,
    });
    loadingWindow.on('closed', () => {
      loadingWindow = null;
    });
  }
  // A new loadURL aborts the previous one; that is deliberately ignored here.
  loadingWindow.loadURL(barPage({ title: TITLE, lang: i18n.currentLanguage(), text: text })).catch(() => {});
}

function closeLoading() {
  if (!loadingWindow) return;
  const win = loadingWindow;
  loadingWindow = null;
  win.destroy();
}

function isSameOrigin(url) {
  try {
    return new URL(url).origin === new URL(serverUrl).origin;
  } catch {
    return false;
  }
}

function isWebUrl(url) {
  try {
    const { protocol } = new URL(url);
    return protocol === 'http:' || protocol === 'https:';
  } catch {
    return false;
  }
}

/** Opens external web links in the system browser; everything else is refused. */
function openInSystemBrowser(url) {
  if (isWebUrl(url)) shell.openExternal(url);
}

function guardNavigation(event, url) {
  if (isSameOrigin(url)) return;
  event.preventDefault();
  openInSystemBrowser(url);
}

/** The Streamlit view sits below the title bar; it is resized with the window. */
function layoutView() {
  if (!mainWindow || mainWindow.isDestroyed() || !mainView) return;
  const [width, height] = mainWindow.getContentSize();
  mainView.setBounds({ x: 0, y: TITLEBAR_HEIGHT, width, height: Math.max(0, height - TITLEBAR_HEIGHT) });
}

/** Main window: title bar page with the Streamlit view below; navigation is limited to the server origin. */
function openMainWindow(url) {
  if (quitting) return;
  const dark = nativeTheme.shouldUseDarkColors;
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    show: false,
    title: TITLE,
    icon: ICON_PATH,
    backgroundColor: contentBackground(dark),
    // The menu stays hidden; the Alt key shows it (it holds Tools and the reload entry).
    autoHideMenuBar: true,
    ...titleBarOptions(process.platform, dark),
    webPreferences: WEB_PREFERENCES,
  });
  mainWindow = win;

  const view = new WebContentsView({ webPreferences: WEB_PREFERENCES, backgroundColor: contentBackground(dark) });
  mainView = view;
  win.contentView.addChildView(view);
  layoutView();
  win.on('resize', layoutView);

  const contents = view.webContents;
  contents.on('will-navigate', guardNavigation);
  contents.on('will-redirect', guardNavigation);
  // Attachments open via target=_blank; they go to the system browser, not a new Electron window.
  contents.setWindowOpenHandler(({ url: target }) => {
    openInSystemBrowser(target);
    return { action: 'deny' };
  });
  win.once('ready-to-show', () => {
    if (!win.isDestroyed()) win.show();
  });
  win.on('closed', () => {
    if (mainWindow === win) {
      mainWindow = null;
      mainView = null;
    }
  });
  win.loadURL(barPage({ title: TITLE, lang: i18n.currentLanguage() })).catch((err) => console.error('Could not load the title bar:', err));
  contents.loadURL(url).catch((err) => console.error('Could not load the viewer:', err));
}

/** Parent for dialogs: the main window, else the loading window, else none. */
function showDialog(options) {
  const parent = mainWindow ?? loadingWindow;
  return parent && !parent.isDestroyed() ? dialog.showMessageBox(parent, options) : dialog.showMessageBox(options);
}

function focusWindow() {
  const win = mainWindow ?? loadingWindow;
  if (!win) return;
  if (win.isMinimized()) win.restore();
  win.focus();
}

async function stopServer() {
  const current = server;
  server = null;
  if (current) await current.stop();
}

/** stopServer for exit paths: logs errors instead of throwing. */
async function stopServerQuietly() {
  try {
    await stopServer();
  } catch (err) {
    console.error('Could not stop the server:', err);
  }
}

/**
 * Runs a start/restart operation. While one is running (or the app is quitting),
 * every further call is ignored and returns null.
 * @param {() => Promise<void>} fn
 * @returns {Promise<void> | null}
 */
function runExclusive(fn) {
  if (backendOp || quitting) return null;
  backendOp = (async () => {
    try {
      await fn();
    } finally {
      backendOp = null;
    }
  })();
  return backendOp;
}

/** The dashboard process died while the app is running: offer a restart or quit. */
function onServerExit({ tail }) {
  if (quitting) return;
  showDialog({
    type: 'error',
    title: TITLE,
    message: t('electron.dialog.server_stopped'),
    detail: tail || undefined,
    buttons: [t('electron.dialog.restart'), t('electron.dialog.quit')],
    defaultId: 0,
    cancelId: 1,
  }).then(({ response }) => {
    if (response === 0) {
      runExclusive(() =>
        restartBackend().catch((err) => {
          closeLoading();
          dialog.showErrorBox(t('electron.dialog.start_failed'), describeError(err));
          app.quit();
        }),
      );
    } else {
      app.quit();
    }
  });
}

/** Starts the server with the chosen runtime. Stops it right away if the app is quitting in the meantime. */
async function startBackend() {
  const handle = await startServer({
    python: runtime.python,
    appRoot: getAppRoot(),
    dataDir: getDataDir(),
  });
  server = handle;
  serverUrl = handle.url;
  handle.onExit(onServerExit);
  if (quitting) await stopServer();
  return handle;
}

/** Restarts the server and reloads the viewer. */
async function restartBackend() {
  await stopServer();
  showLoading(t('electron.loading.start_dashboard'));
  await startBackend();
  if (quitting) return;
  if (mainView) {
    mainView.webContents.loadURL(serverUrl).catch((err) => console.error('Could not load the viewer:', err));
  } else {
    openMainWindow(serverUrl);
  }
  closeLoading();
}

/** Tools menu: rebuild the Python environment (system Python only), then restart the server. */
async function reinstallPython() {
  try {
    runtime = await resolveRuntime({ ...runtimeOptions(), force: true });
    await restartBackend();
  } catch (err) {
    closeLoading();
    dialog.showErrorBox(t('electron.dialog.start_failed'), describeError(err));
    // Without a running server the viewer is no longer usable.
    if (!server) app.quit();
  }
}

function buildMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{ role: 'appMenu' }] : []),
    { role: 'fileMenu' },
    { role: 'editMenu' },
    {
      // Own reload entry: the reload role would reload the title bar page, not the dashboard.
      role: 'viewMenu',
      submenu: [
        { label: t('electron.menu.reload'), accelerator: 'CmdOrCtrl+R', click: () => mainView && mainView.webContents.reload() },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    { role: 'windowMenu' },
    {
      label: t('electron.menu.tools'),
      submenu: [
        {
          label: t('electron.menu.reinstall_python'),
          enabled: runtime !== null && runtime.mode === 'system',
          click: () => runExclusive(reinstallPython),
        },
        {
          label: t('electron.menu.open_data_folder'),
          click: () => shell.openPath(getDataDir() ?? getAppRoot()),
        },
      ],
    },
  ];
  return Menu.buildFromTemplate(template);
}

/** One-time notice when data of the former Windows build was found next to the new data folder. */
async function showLegacyNoticeOnce() {
  const userDataDir = app.getPath('userData');
  const legacy = await shouldShowLegacyNotice({ userDataDir, platform: process.platform });
  if (!legacy) return;
  const { response } = await showDialog({
    type: 'info',
    title: TITLE,
    message: t('electron.dialog.legacy_title'),
    detail: t('electron.dialog.legacy_body', { dbPath: legacy.dbPath, userData: userDataDir }),
    buttons: [t('electron.dialog.open_folder'), t('electron.dialog.ok')],
    defaultId: 1,
    cancelId: 1,
  });
  if (response === 0) shell.showItemInFolder(legacy.dbPath);
  await writeShellState(userDataDir, { ...(await readShellState(userDataDir)), legacyNoticeShown: true });
}

async function startup() {
  i18n.init({ preferred: app.getPreferredSystemLanguages() });
  showLoading(t('electron.loading.find_python'));
  runtime = await resolveRuntime(runtimeOptions());
  Menu.setApplicationMenu(buildMenu());
  showLoading(t('electron.loading.start_dashboard'));
  await startBackend();
  if (quitting) return;
  if (SMOKE) {
    await finishSmoke();
    return;
  }
  openMainWindow(serverUrl);
  closeLoading();
  showLegacyNoticeOnce().catch((err) => console.error('Could not show the legacy notice:', err));
}

/** Smoke test: GET / against the running server, then stop the server and quit with 0 or 1. */
async function finishSmoke() {
  const ok = await runSmoke(serverUrl);
  console.log(ok ? `Smoke test passed: ${serverUrl}` : `Smoke test failed: ${serverUrl}`);
  await stopServer();
  // The loading window stays open until app.exit, so no window-all-closed quit gets in between.
  app.exit(ok ? 0 : 1);
}

function onBeforeQuit(event) {
  if (quitting) return;
  quitting = true;
  event.preventDefault();
  // Wait for a running start/restart operation first (ignoring errors), so no server is left behind.
  const pending = backendOp ? backendOp.catch(() => {}) : Promise.resolve();
  pending
    .then(() => stopServer())
    .catch((err) => console.error('Could not stop the server:', err))
    .finally(() => app.quit());
}

async function run() {
  await app.whenReady();
  nativeTheme.on('updated', applyChromeColors);
  try {
    await runExclusive(startup);
  } catch (err) {
    if (SMOKE) {
      console.error(describeError(err));
      // app.exit skips before-quit, so a server started before the error is stopped explicitly.
      await stopServerQuietly();
      app.exit(1);
      return;
    }
    closeLoading();
    // No error dialog while quitting; onBeforeQuit quits the app anyway.
    if (quitting) return;
    dialog.showErrorBox(t('electron.dialog.start_failed'), describeError(err));
    // app.exit skips before-quit, so a server started before the error is stopped explicitly.
    await stopServerQuietly();
    app.exit(1);
  }
}

if (!app.requestSingleInstanceLock()) {
  if (SMOKE) {
    console.error('Another instance is already running.');
    app.exit(1);
  } else {
    app.quit();
  }
} else {
  app.on('second-instance', focusWindow);
  app.on('before-quit', onBeforeQuit);
  app.on('window-all-closed', () => app.quit());
  run();
}
