const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PACKAGE_JSON = path.join(ROOT, 'electron', 'package.json');
const VERSION_FILE = path.join(ROOT, 'electron', 'VERSION');
function normalizeElectronVersion(version) {
  return String(version)
    .replace(/\.post(?=\d+)/g, '-post')
    .replace(/\.dev(?=\d+)/g, '-dev');
}
function fetchVersionFromPython() {
  const python = process.env.PYTHON_EXECUTABLE || 'python';
  const script = [
    'import sys',
    'from pathlib import Path',
    'root = Path(\'.\').resolve()',
    'sys.path.insert(0, str(root / \"src\"))',
    'sys.path.insert(0, str(root))',
    'from src.version import get_canonical_version',
    'print(get_canonical_version())',
  ].join('; ');

  try {
    return execFileSync(python, ['-c', script], {
      cwd: ROOT,
      encoding: 'utf8',
    }).trim();
  } catch (error) {
    console.error('Error resolving canonical version from Python:', error.message);
    process.exit(1);
  }
}

function updateElectronPackage(version) {
  const normalizedVersion = normalizeElectronVersion(version);
  const packageJson = JSON.parse(fs.readFileSync(PACKAGE_JSON, 'utf8'));
  if (packageJson.version !== normalizedVersion) {
    packageJson.version = normalizedVersion;
    fs.writeFileSync(PACKAGE_JSON, JSON.stringify(packageJson, null, 2) + '\n', 'utf8');
    return true;
  }
  return false;
}

function writeVersionArtifact(version) {
  const currentVersion = fs.existsSync(VERSION_FILE)
    ? fs.readFileSync(VERSION_FILE, 'utf8').trim()
    : null;

  if (currentVersion !== version) {
    fs.writeFileSync(VERSION_FILE, version + '\n', 'utf8');
    return true;
  }
  return false;
}

function syncElectronVersionArtifact(version) {
  const packageUpdated = updateElectronPackage(version);
  const artifactUpdated = writeVersionArtifact(version);
  return packageUpdated || artifactUpdated;
}

const version = fetchVersionFromPython();
const updated = syncElectronVersionArtifact(version);
console.log(`Electron package version ${updated ? 'updated' : 'already in sync'} -> ${version}`);
