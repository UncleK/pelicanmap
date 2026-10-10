import { existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const venv = process.platform === 'win32'
  ? join(root, '.venv', 'Scripts', 'python.exe')
  : join(root, '.venv', 'bin', 'python');
const python = existsSync(venv) ? venv : 'python';
const [script, ...args] = process.argv.slice(2);
if (!script) throw new Error('Python script path is required');
const result = spawnSync(python, ['-B', script, ...args], {
  cwd: root, stdio: 'inherit', windowsHide: true,
});
if (result.error) throw result.error;
process.exit(result.status ?? 1);
