"""Run a renderer command and save its real output, timing and source hashes."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
name, *command = sys.argv[1:]
run = root / 'run'
run.mkdir(exist_ok=True)
files = [root / n for n in ['index.html', 'scene.js', 'build.mjs', 'export_meshes.py',
                           'package.json', 'pnpm-lock.yaml', 'index.motion.json']]
files += sorted((root / 'assets').glob('*'))
hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
started = datetime.now(timezone.utc).isoformat()
tick = time.monotonic()
result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
duration = time.monotonic()-tick
text = result.stdout.replace(str(root), '<video>').replace(str(Path.home()), '<home>')
text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
(run / (name + '.log')).write_text(text)
(run / (name + '.json')).write_text(json.dumps({
    'started_at_utc': started,
    'elapsed_seconds': round(duration, 3),
    'command': [part.replace(str(Path.home()), '<home>') for part in command],
    'exit_code': result.returncode,
    'source_sha256': hashes,
}, indent=2)+'\n')
print(text)
sys.exit(result.returncode)
