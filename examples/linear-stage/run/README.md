# Execution record

English · [简体中文](README.zh-CN.md) · [Example](../README.md)

Authoring agent: **Codex in this repository-maintenance conversation**, on 2026-10-23. CAD execution: local Python 3.12 and build123d 0.11.0. The [brief](../brief.md) records the adopted requirements and modeling decisions; it is not a transcript from another agent product.

Each numbered `.log` captures a command's output and exit code. The matching `.json` records its UTC start time, elapsed command time, and source hashes. Commands use `python` in place of the local interpreter path; tracebacks abbreviate the checkout path as `<example>`. These timings cover the scripts, not the agent's total design time.

| Step | Evidence | Outcome |
|---|---|---|
| Build the first 80 mm model | [01 log](01-build-80.log), [initial source](snapshots/01-initial-model.py) | Export stopped: build123d 0.11.0's `Color` has no `to_tuple()` method. |
| Fix color serialization | [02 log](02-build-80.log), [source](snapshots/02-export-fix-model.py) | Changed to `list(shape.color)`; exported 36 parts. |
| Check geometry and motion | [03 log](03-check-80.log), [check source](snapshots/02-initial-check.py), [failed model](../generated/initial-80/assembly.step) | Five fixed-component interference pairs. Nine carriage positions had no moving/fixed interference. |
| Repair the assembly | [04 build](04-build-80-fixed.log), [05 check](05-check-80-fixed.log), [source](snapshots/04-clearance-fix-model.py) | Added a motor clearance pocket, shifted the two mount bolts by 0.8 mm, and bored the motor front plate for the shaft. Checks passed. |
| Freeze the baseline | [SHA-256 manifest](frozen-80-sha256.json) | Recorded the accepted 80 mm files, model/check sources, and original configuration before the revision. |
| Increase travel to 120 mm | [06 build](06-build-120.log), [07 check](07-check-120.log), [config](snapshots/06-config.json) | Changed `travel` from 80 to 120; geometry and nine-position checks passed. |
| Rebuild the original size | [08 build](08-rebuild-80.log), [09 check](09-check-rebuilt-80.log) | Final model code still builds the accepted 80 mm assembly. |
| Compare saved variants | [10 first comparison](10-compare-variants.log), [original comparison source](snapshots/10-initial-compare.py), [12 corrected comparison](12-compare-fixed.log) | A coincident-cylinder Boolean `Common` returned empty for the translated motor shaft. Direct two-way subtraction confirmed identical geometry. The corrected comparison passed without increasing the volume tolerance. |
| Cross-check interference | [13 audit](13-collision-audit.log) | A separate cut-volume calculation agreed with the collision checks for every broad-phase candidate in both variants. |
| Render the STEP files | [11 preview](11-render.log), [15 final render](15-render-labels.log) | Produced assembly, exploded and same-scale comparison views; adjusted the comparison camera to include the whole motor. |

The original five interference volumes were 1680 mm³ (base/motor), 84 mm³ (base/front plate), 0.079145 mm³ for each of two bolt heads touching the front plate, and 78.539816 mm³ (front plate/shaft). The fixed model passes with the same 0.00001 mm³ threshold.

[Final revision checks](../generated/revision-checks.json) identify exactly four changed part geometries: base, two guide rods, and lead screw. They also confirm that the frozen files are unchanged and every rebuilt 80 mm part matches its baseline using solid symmetric difference.

The figures show the actual exported geometry. Exploded offsets are applied only by the renderer; interference checks use assembled positions. Threads and bearing internals are simplified, and the motion check samples nine positions rather than proving continuous clearance.
