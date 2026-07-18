const { app, BrowserWindow, dialog } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const net = require('net');
const path = require('path');

const HOST = '127.0.0.1';
const PORT = Number(process.env.STREAMLIT_PORT || process.env.PORT || 8501);
const STREAMLIT_URL = `http://${HOST}:${PORT}`;
const APP_ROOT = path.resolve(__dirname, '..');
const PACKAGED_PYTHON_RUNTIME = path.join(process.resourcesPath, 'python-runtime');
const DEV_PYTHON_RUNTIME = path.join(APP_ROOT, 'electron', 'python-runtime');

let pythonProcess = null;
let mainWindow = null;

function getPythonExecutable() {
  if (process.env.PYTHON_EXECUTABLE) {
    return process.env.PYTHON_EXECUTABLE;
  }

  for (const runtimePath of [PACKAGED_PYTHON_RUNTIME, DEV_PYTHON_RUNTIME]) {
    if (fs.existsSync(runtimePath)) {
      if (process.platform === 'win32') {
        return path.join(runtimePath, 'Scripts', 'python.exe');
      }
      return path.join(runtimePath, 'bin', 'python');
    }
  }

  return process.platform === 'win32' ? 'python.exe' : 'python3';
}

function waitForServer(host, port, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    const attempt = () => {
      const socket = new net.Socket();
      socket.setTimeout(1000);
      socket.once('error', () => {
        socket.destroy();
        if (Date.now() - startTime > timeout) {
          reject(new Error(`Streamlit did not become available within ${timeout}ms`));
        } else {
          setTimeout(attempt, 300);
        }
      });
      socket.once('timeout', () => {
        socket.destroy();
        if (Date.now() - startTime > timeout) {
          reject(new Error(`Streamlit did not become available within ${timeout}ms`));
        } else {
          setTimeout(attempt, 300);
        }
      });
      socket.connect(port, host, () => {
        socket.end();
        resolve();
      });
    };

    attempt();
  });
}

function startStreamlit() {
  const python = getPythonExecutable();
  const args = [
    '-m',
    'streamlit',
    'run',
    'dashboard/app.py',
    '--server.headless',
    'true',
    '--server.address',
    HOST,
    '--server.port',
    String(PORT),
    '--server.enableCORS',
    'false',
    '--server.enableXsrfProtection',
    'false',
  ];

  pythonProcess = spawn(python, args, {
    cwd: APP_ROOT,
    env: process.env,
  });

  pythonProcess.stdout.on('data', (chunk) => {
    console.log(`[Streamlit] ${chunk.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (chunk) => {
    console.error(`[Streamlit] ${chunk.toString().trim()}`);
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`Streamlit process exited with code=${code} signal=${signal}`);
    pythonProcess = null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.close();
    }
  });

  pythonProcess.on('error', (error) => {
    dialog.showErrorBox('Streamlit Launch Error', error.message);
    stopStreamlit();
    app.quit();
  });
}

function stopStreamlit() {
  if (pythonProcess && !pythonProcess.killed) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(STREAMLIT_URL);
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

async function start() {
  try {
    startStreamlit();
    await waitForServer(HOST, PORT, 30000);
    createWindow();
  } catch (error) {
    dialog.showErrorBox('Streamlit startup failed', error.message);
    stopStreamlit();
    app.quit();
  }
}

app.on('ready', start);

app.on('before-quit', () => {
  stopStreamlit();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
