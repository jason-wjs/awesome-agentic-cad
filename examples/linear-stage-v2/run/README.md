# Run record — 23 October 2026

[简体中文](README.zh-CN.md) · [Example](../README.md)

Codex split this iteration into modeling, independent geometry checks, and video production, then reviewed the renders and assembled the two README versions. The inputs were the first stage model and the request to improve its mechanical detail, exploded view, motion, and travel comparison. Logs below record executed commands; this page summarizes the work rather than reproducing the conversation.

| Work | Record | Outcome |
|---|---|---|
| First detailed 80 mm model | [model-01](model-01-initial-80.log) | The screw exported as three solids. The helical section and shaft journals needed overlap. |
| Connected screw; volume investigation | [model-02](model-02-connected-80.log), [model-03](model-03-adaptive-80.log), [model-04](model-04-adaptive-120.log) | The screw became one valid solid. Source and STEP volume integrals still differed. |
| Preserve native geometry for comparison | [model-05](model-05-native-proof-120.log), [model-06](model-06-native-proof-80.log) | Saved native screw BREP alongside STEP. The two-way geometric differences are empty. |
| Exercise the checker | [check-00](check-00-positive-controls.log), [check-01](check-01-80.log), [check-02](check-02-positive-controls-adaptive.log), [check-03](check-03-positive-controls-adaptive.log), [check-04](check-04-120.log) | Fixed a Boolean-result API mismatch and the hole-height expectation after adding counterbores. Positive controls detect known overlaps and distinguish contact from penetration. |
| Check both travel variants | [check-05](check-05-80-report.json), [check-06](check-06-120-report.json) | Both pass: 59 parts, 15 sampled poses, no detected interference, 6 mm end clearance. |
| Rebuild and compare | [model-07](model-07-rebuilt-80.log), [check-07](check-07-revision-report.json) | All 59 rebuilt 80 mm parts match. Four parts change shape with longer travel; 55 retain their local geometry. |
| Render static views | [prepare 80](render-prepare-80-01.log), [prepare 120](render-prepare-120-01.log), [views](render-views-01.log), [v1 comparison](render-baseline-01.log) | text-to-cad/cadgen 0.7.26, materials and staged explosion applied to presentation copies. |
| Render motion | [Video records](../video/run/README.md) | 24-second MP4 and GIF; assembly, coupled motion, explosion and same-scale travel comparison. |
| Homepage teaser, 24 October | [Conversion record](../video/run/10-teaser.json) | Replaced the original media delivery with one 12-second GIF at 2× speed. The MP4 is kept as a local intermediate. |

Commands have neighboring JSON records with source hashes and timing. The recovered `check-02` error record has no timing or input hashes. Historical sources are in [snapshots](snapshots); failed attempts are retained. Geometry checks also record input hashes. [frozen-80-sha256.json](frozen-80-sha256.json) tracks the accepted 80 mm model, checker, configuration, and CAD outputs through the revision comparison.

The CAD runs used Python 3.12.14, build123d 0.11.0, and cadquery-ocp-novtk 7.9.3.1.1. Rendering ran separately with cadgen 0.7.26 and build123d 0.11.1, using installed Chrome through [cadgen_cli.py](../cadgen_cli.py). The video has its own pinned dependencies and output hashes.
