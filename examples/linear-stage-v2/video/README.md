# Linear-stage motion

This composition renders a 12-second GIF at 2× speed. It shows the assembly, a carriage traverse, a staged exploded view, and an 80/120 mm comparison at the same scale, using the exported STEP parts from both travel variants.

The 24-second source sequence renders to a local MP4 in the ignored `out/` directory, then FFmpeg converts it with [make_teaser.py](../make_teaser.py).

`scene.js` drives a Three.js scene from HyperFrames time. Every pose is computed from its timestamp. Carriage motion follows the model's signed rotation-per-millimeter value; the screw, coupling, shaft collars, and motor shaft turn together. Exploded offsets come from the part manifest. They illustrate component relationships, not a verified installation sequence.

The mesh exporter preserves CAD face boundaries. Cylinders shade smoothly without rounding sharp edges. Material colors, roughness and metalness come from the same manifest used for the static renders.

## Reproduce

Requires Python with the example's CAD dependencies, Node.js 22 or later, pnpm, and FFmpeg. From this directory:

```bash
python export_meshes.py --source ../generated/80 --output assets/stage-80
python export_meshes.py --source ../generated/120 --output assets/stage-120
pnpm install --frozen-lockfile
pnpm run build
pnpm run check
pnpm run render
pnpm run teaser
```

To convert an existing render directly, run `python ../make_teaser.py out/stage-motion.mp4 ../../../assets/stage-motion.gif`. The exporter sets 2× speed, 800-pixel width, 12 fps, a 96-color palette, and an infinite loop.

The pinned rendering libraries are bundled into `assets/scene.bundle.js`. Mesh files are compressed and loaded locally before the timeline is ready. There are no external image, model or texture requests during rendering.

Three.js's license is retained in `licenses/`; the bundle's license notices also retain the GSAP copyright and license URL.

`run/` contains the render log, source hashes, checks and media metadata from the earlier homepage teaser.
