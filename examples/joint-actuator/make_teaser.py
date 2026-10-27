"""Encode the 12-second CAD render as a compact looping GIF."""
from pathlib import Path
import argparse
import subprocess

p = argparse.ArgumentParser()
p.add_argument('input', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--width', type=int, default=880)
p.add_argument('--fps', type=int, default=12)
p.add_argument('--colors', type=int, default=128)
a = p.parse_args()
a.output.parent.mkdir(parents=True, exist_ok=True)
filters = (f'fps={a.fps},scale={a.width}:-1:flags=lanczos,split[s0][s1];'
           f'[s0]palettegen=max_colors={a.colors}:reserve_transparent=1:stats_mode=diff[p];'
           '[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle')
subprocess.run(['ffmpeg', '-y', '-i', str(a.input), '-filter_complex', filters,
                '-loop', '0', '-an', str(a.output)], check=True)
