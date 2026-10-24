"""Add presentation metadata to saved STEP, then render with text-to-cad/cadgen.

Run with cadgen==0.7.26 installed. The checked assembly.step files are inputs;
view.step is a separate presentation copy with PBR materials and an explode clip.
"""
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
os.environ.setdefault('CADGEN_TELEMETRY', '0')


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def command(label, args):
    records = HERE/'run'
    records.mkdir(exist_ok=True)
    previous = list(records.glob(f'render-{label}-*.json'))
    stem = f'render-{label}-{len(previous)+1:02d}'
    sources = {p.name: sha256(p.read_bytes()).hexdigest() for p in (HERE/'render.py', HERE/'cadgen_cli.py')}
    snap = records/'snapshots'/stem
    snap.mkdir(parents=True, exist_ok=True)
    for name in sources:
        (snap/name).write_bytes((HERE/name).read_bytes())
    start = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    result = subprocess.run([sys.executable, str(HERE/'cadgen_cli.py'), *args], cwd=HERE,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = result.stdout.replace(str(HERE), '<example>').replace(str(Path.home()), '<home>')
    (records/f'{stem}.log').write_text('$ python cadgen_cli.py '+' '.join(args)+'\n'+output)
    save(records/f'{stem}.json', {'started_utc': start, 'duration_seconds': round(time.monotonic()-clock, 3),
        'command': ['python', 'cadgen_cli.py', *args], 'exit_code': result.returncode,
        'cadgen_version': version('cadgen'), 'source_sha256': sources})
    print(output, flush=True)
    result.check_returncode()


def prepare(travel):
    folder = HERE/'generated'/str(travel)
    manifest = json.loads((folder/'manifest.json').read_text())
    definitions, assignments, offsets = {}, [], []
    for part in manifest['parts']:
        material = part['material']
        key = material['name']
        definitions[key] = {k: material[k] for k in ('metalness', 'roughness')}
        assignments.append({'targets': ['#'+part['name']], 'material': key})
        offsets.append([part['name'], part['explode']['offset_mm'], part['explode']['stage']])
    save(folder/'materials.json', {'definitions': definitions, 'assignments': assignments})
    source = 'const parts = '+json.dumps(offsets)+';\n'+'''
const ease = x => { x = Math.max(0, Math.min(1, x)); return x*x*(3-2*x); };
export const clips = {
  explode: { label: "Layered exploded view", duration: 8, loop: false,
    update(t, m) {
      for (const [name, offset, stage] of parts) {
        const f = stage ? ease((t-(stage-1)*0.6)/1.2) : 0;
        m.get(name).translate(offset.map(v => v*f));
      }
    }
  }
};
'''
    (folder/'explode.js').write_text(source)
    prefix = f'generated/{travel}'
    command(f'prepare-{travel}', ['step', 'build', f'{prefix}/assembly.step', f'{prefix}/view.step',
        '--materials', f'{prefix}/materials.json', '--animation', f'{prefix}/explode.js', '--json'])


def render():
    jobs = []
    camera = {'direction': [0.65, -1, 0.7]}
    for travel in (80, 120):
        jobs.append({'input': f'generated/{travel}/view.step', 'preview': True,
            'camera': camera, 'outputs': [{'path': f'generated/assembly-{travel}.png', 'width': 2000, 'height': 1150}],
            'output': {'padding': 0.08}})
    jobs.append({'input': 'generated/120/view.step', 'preview': True,
        'camera': {'direction': [0.4, -1, 0.65]}, 'animation': {'clip': 'explode', 'time': 7},
        'outputs': [{'path': 'generated/exploded.png', 'width': 2000, 'height': 1450}],
        'output': {'padding': 0.08}})
    save(HERE/'render-jobs.json', {'jobs': jobs})
    command('views', ['snapshot', '--job', 'render-jobs.json', '--json'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--render-only', action='store_true')
    args = parser.parse_args()
    if not args.render_only:
        for travel in (80, 120):
            prepare(travel)
    if not args.prepare_only:
        render()
