---
workflow: general-video
flow: automation
storyboard: no
message: A real CAD assembly can move, separate into its components, and adapt to a longer travel.
destination: github-readme
aspect: 1280x720
language: en
length: 24s
voice: none
---

## Intent

Show the refined screw-driven linear stage with enough mechanical detail to read the mechanism. The user approved the next polish pass, including assembly motion, exploded assembly, and the 80 to 120 mm revision. Keep the model larger than the typography and keep the film silent.

## Assets

- `../generated/80/` — STEP geometry and part metadata for the initial variant.
- `../generated/120/` — independently generated STEP geometry for the longer variant.

## Customizations

- Use actual STEP tessellation, PBR materials, a studio environment and ground shadows.
- Relate screw angle to carriage displacement through the model's 4 mm lead.
- Separate parts in groups and reverse the sequence to reassemble.
- Show both travel variants at the same scale.

## Notes

The exploded arrangement is an illustration of component relationships, not a collision-free installation plan. Rendering is explicitly included in the approved work. This project uses a Three.js scene driven only by HyperFrames time.
