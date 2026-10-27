# Build and check record

**English** · [简体中文](README.zh-CN.md) · [Example](../README.md)

Codex modeled the supplied joint-actuator cutaway in build123d, generated the 20 mm bore assembly, and enlarged the bore to 30 mm. The external dimensions and mounting patterns stayed fixed.

| Record | Contents |
|---|---|
| [20 mm build](model-20.json), [30 mm build](model-30.json) | Source and configuration hashes, exported STEP hashes, part counts, elapsed time. |
| [Checks](check.json) | Run time and controls for overlap, contact, a blocked bore, and a blocked screw-entry path. |
| [20 mm geometry](check-bore-20.json), [30 mm geometry](check-bore-30.json) | Solid validity, STEP round trips, bore and mounting measurements, bearing clearances, interference, screw insertion, cutaway checks. |
| [Revision](revision.json) | Eight changed parts; unchanged outer envelope and mounting geometry outside the enlarged bore. |

The detail pass added denser windings, insulating bobbins, curved magnet faces, rounded teeth, and grooved bearing races. Inspection of the front screws exposed a lip across their entry holes. Opening the counterbores removed it; the checker now sweeps each screw's head and shank from the front to its installed position.

Each variant contains 91 named components and 510 solids. The interference check screens all 4,095 component pairs, performs exact intersections for overlapping bounding boxes, and also checks solids within compound components. The reports cover the modeled static geometry; tooth deformation, bearing preload, and torque are not calculated.

Blender Cycles renders meshes and surface normals exported from these STEP parts. HyperFrames adds the labels and comparison layout. Source files and render records are in [video/](../video/).
