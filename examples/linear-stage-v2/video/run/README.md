# Render record

The current homepage asset is the 12-second, 2×-speed GIF recorded in `10-teaser.json` and `.log` on 24 October 2026. The MP4 is now a local intermediate; the earlier media records below describe the original 24-second delivery.

- `06-check.log`: final HyperFrames lint, runtime, layout and contrast checks. No errors; all 23 text checks passed. The film is intentionally silent.
- `07-render.log` and `.json`: final MP4 render, UTC start, elapsed time and source hashes.
- `08-gif.log` and `.json`: the smaller GIF encoded from that MP4.
- `media-mp4.json` and `artifact-checks.json`: encoded dimensions, duration, frame rate, file hashes, and STEP-to-mesh source checks.

The earlier render revealed a support reaching the title during the traverse. The camera was pulled back and lowered before the final encode. `snapshots/pre-framing-scene.js` and its bundle reproduce that earlier view and match the recorded hashes.

The optional DOM motion audit timed out. The canvas was instead checked at the operating endpoints, full exploded pose, reassembled pose and travel comparison; those encoded frames were visually inspected. The keyframe tool's DOM target list does not describe the internal Three.js transforms.

Logs retain real tool output with local home-directory paths replaced by `<home>` and terminal control codes removed.

`snapshots/pre-teaser-package.json` preserves the package scripts used for the original render. The current scripts render the MP4 into ignored `out/`, then export the teaser GIF.
