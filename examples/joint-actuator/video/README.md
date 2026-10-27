# Joint actuator animation

The STEP parts are tessellated with CAD surface normals and rendered in Blender Cycles. HyperFrames adds the short phase labels and the bore comparison, then FFmpeg encodes the 12-second GIF.

Requires Python 3.12, Blender 4.5, Node.js 22+, pnpm and FFmpeg. Install the example's `requirements.txt` first. From `examples/joint-actuator`:

```bash
python model.py --config config-20.json --output generated/bore-20
python model.py --config config-30.json --output generated/bore-30
python video/export_meshes.py --source generated/bore-20 --output video/assets/joint-20
python video/export_meshes.py --source generated/bore-30 --output video/assets/joint-30
cd video
python render.py --blender /path/to/blender
pnpm install --frozen-lockfile
pnpm run build
pnpm run check
pnpm run render
pnpm run teaser
```

`BLENDER` can be used instead of `--blender`. On macOS, an installed Blender executable is usually `/Applications/Blender.app/Contents/MacOS/Blender`.

[`render_cad.py`](render_cad.py) defines the materials, studio lighting, cameras and exploded positions. It renders 128-sample stills and 64-sample animation frames with OpenImageDenoise. The 20 mm and 30 mm comparison views use the same orthographic camera and scale. The gears remain rigid.

The GIF is written to [`assets/joint-actuator.gif`](../../../assets/joint-actuator.gif) at 880 × 495, 12 fps and 128 colors. `out/cad/` contains the unlabelled stills and the frame sequence; intermediate MP4 files stay in the ignored `out/` directory. Individual STEP parts, meshes and the JavaScript bundle are regenerated locally.

Run `python render.py --mode stills` for still images only. Final commands, renderer settings and input/output hashes are recorded in [`run/`](run/).
