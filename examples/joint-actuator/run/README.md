# Build and check record

**English** · [简体中文](README.zh-CN.md) · [Example](../README.md)

Codex modeled the supplied joint-actuator cutaway in build123d, generated the 20 mm bore assembly, and enlarged the bore to 30 mm. The external dimensions and mounting patterns stayed fixed.

| Record | Contents |
|---|---|
| [20 mm build](model-20.json), [30 mm build](model-30.json) | Source and configuration hashes, exported STEP hashes, part counts, elapsed time. |
| [Checks](check.json) | Run time and checker controls for overlap, contact, and an obstructed bore. |
| [20 mm geometry](check-bore-20.json), [30 mm geometry](check-bore-30.json) | Solid validity, STEP round trips, bore and mounting measurements, clearances, interference, cutaway checks. |
| [Revision](revision.json) | Six changed parts; unchanged outer envelope and mounting geometry outside the enlarged bore. |

Early checks caught reversed magnet extrusion, housing intrusion into the stator, overlapping encoder contacts, and duplicated STEP assembly instances. Those were corrected before the final exports. The cutaway was then adjusted to retain copper coils and their pole teeth.

Each variant contains 56 named parts and 254 solids. The interference check screens all 1,540 part pairs, performs exact intersections for overlapping bounding boxes, and also checks solids within compound parts. The reports cover the modeled static geometry; tooth deformation, bearing preload, and torque are not calculated.

The animation uses meshes tessellated from these STEP parts. Its source and render records are in [video/](../video/).
