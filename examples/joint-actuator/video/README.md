# Joint actuator animation

A 12-second GIF rendered from the two STEP assemblies with Three.js and HyperFrames. The sequence shows a cutaway, the closed assembly, an axial exploded view, and the 20 → 30 mm bore change. The gears remain rigid throughout.

Python 3.12, Node.js 22+, pnpm and FFmpeg are required. From `examples/joint-actuator`, after installing `requirements.txt`:

```bash
python model.py --config config-20.json --output generated/bore-20
python model.py --config config-30.json --output generated/bore-30
python video/export_meshes.py --source generated/bore-20 --output video/assets/joint-20
python video/export_meshes.py --source generated/bore-30 --output video/assets/joint-30
cd video
pnpm install --frozen-lockfile
pnpm run build
pnpm run check
pnpm run render
pnpm run teaser
```

The first two commands regenerate the individual STEP parts, which are omitted from Git. `export_meshes.py` tessellates those parts and their cutaway versions. Meshes and the JavaScript bundle are also regenerated locally.

The GIF is written to [`assets/joint-actuator.gif`](../../../assets/joint-actuator.gif). The intermediate MP4 stays in the ignored `out/` directory. `make_teaser.py` produces an 800 × 450, 12 fps GIF with a 96-color palette.

[`scene.js`](scene.js) contains the camera, lighting and time-based part positions. The split-screen comparison uses identical cameras and scales. A subtle surface shader adds turning marks to aluminium; it does not change the STEP geometry.

Validation and output hashes are in [`run/`](run/).
