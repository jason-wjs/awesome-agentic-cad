---
mode: autonomous
status: build
message: A CAD assembly can move, separate into its components, and adapt to a longer travel.
---

## Frame 1

status: outline
src: index.html
time: 0–3 s
motion: `multi-phase-camera`, implemented with the HyperFrames Three.js adapter.

Introduce the assembled 80 mm stage with a restrained orbit.

## Frame 2

status: outline
src: index.html
time: 3–8 s
motion: Three.js deterministic object transforms and the model's screw-lead constraint.

The carriage traverses and returns to the center. Screw, coupling, and motor shaft rotate together. Display the displacement and 4 mm/rev lead.

## Frame 3

status: outline
src: index.html
time: 8–18 s
motion: Three.js staged translation with smoothstep interpolation; `multi-phase-camera` pullback.

Fasteners separate first, then platform, guide/nut parts, and drive/support components. Hold the exploded pose, then reverse all stages to reassemble.

## Frame 4

status: outline
src: index.html
time: 18–24 s
motion: Three.js side cameras at identical scale; independent carriage travel.

Show 80 and 120 mm variants together, with dimensional travel arrows. Both use the same platform and motor interfaces.
