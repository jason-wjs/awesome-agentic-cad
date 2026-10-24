#!/usr/bin/env python3
"""Convert the 24-second CAD render to a looping 12-second GIF teaser.

Usage: python make_teaser.py INPUT.mp4 OUTPUT.gif
Requires FFmpeg on PATH. The CAD scene does not need to be rendered again.
"""

import argparse
import shlex
import subprocess
from pathlib import Path


FILTER = (
    "setpts=0.5*(PTS-STARTPTS),fps=12,scale=800:-1:flags=lanczos,"
    "split[s0][s1];"
    "[s0]palettegen=max_colors=96:reserve_transparent=1:stats_mode=diff[p];"
    "[s1][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-hide_banner", "-y", "-i", str(args.input),
        "-filter_complex", FILTER, "-an", "-loop", "0", str(args.output),
    ]
    print(shlex.join(command), flush=True)
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
