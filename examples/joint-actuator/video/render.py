"""Render the CAD layers with Cycles, then encode the nine-second motion clip."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--blender', default=os.environ.get('BLENDER', 'blender'))
parser.add_argument('--mode', choices=['hero', 'exploded', 'stills', 'animation', 'all'], default='all')
parser.add_argument('--samples', type=int, default=64)
args = parser.parse_args()
blender = shutil.which(args.blender)
if blender is None:
    parser.error('Blender is required. Set BLENDER or pass --blender /path/to/blender.')
output = ROOT/'out'/'cad'
output.mkdir(parents=True, exist_ok=True)
command = [blender, '--background', '--factory-startup', '--python', 'render_cad.py',
           '--', '--assets', 'assets', '--output', 'out/cad', '--mode', args.mode,
           '--samples', str(args.samples), '--width', '1280', '--height', '720', '--fps', '12']
started = time.monotonic()
log = ROOT/'out'/f'cycles-{args.mode}.log'
with log.open('w') as stream:
    result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
if result.returncode:
    raise SystemExit(f'Cycles failed; see {log}')
if args.mode in ['animation', 'all']:
    subprocess.run(['ffmpeg', '-y', '-framerate', '12', '-i', str(output/'frames'/'frame-%04d.png'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', str(ROOT/'out'/'cad-motion.mp4')], check=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

sources = {name: sha(ROOT/name) for name in ['render.py', 'render_cad.py', 'export_meshes.py']}
meshes = {}
for bore in [20, 30]:
    path = ROOT/'assets'/f'joint-{bore}.json'
    if path.exists():
        data = json.loads(path.read_text())
        meshes[str(bore)] = {'manifest_sha256': data['source_sha256']['manifest.json'],
                             'mesh_sha256': data['mesh_sha256'], 'tessellation': data['tessellation']}
record = {'mode': args.mode, 'command': ['blender', *command[1:]],
          'elapsed_seconds': round(time.monotonic()-started, 2), 'source_sha256': sources,
          'meshes': meshes, 'engine': 'Blender Cycles', 'blender_version': subprocess.check_output(
              [blender, '--version'], text=True).splitlines()[0],
          'animation_samples': args.samples, 'stills_samples': max(128, args.samples),
          'denoiser': 'OpenImageDenoise', 'seed': 7}
(ROOT/'run').mkdir(exist_ok=True)
(ROOT/'run'/f'cycles-{args.mode}.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'mode': args.mode, 'elapsed_seconds': record['elapsed_seconds'], 'output': 'out/cad'}))
