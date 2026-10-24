# Source notes

Reviewed on 2026-10-23 against upstream documentation. The catalog descriptions summarize upstream documentation. The local linear-stage example was built, revised, and checked with build123d 0.11.0; its execution record is linked below.

| Project | Source used |
|---|---|
| CadQuery | [README](https://github.com/CadQuery/cadquery): Python modeling, assemblies, exports. |
| build123d | [README](https://github.com/gumyr/build123d) and [assembly docs](https://build123d.readthedocs.io/en/latest/assemblies.html): modeling interfaces, geometry, assembly, exchange. |
| FreeCAD | [README](https://github.com/FreeCAD/FreeCAD): desktop modeling, Python API, constraints, drawings. |
| text-to-cad | [README](https://github.com/earthtojake/text-to-cad): agent plugins/skills, build123d, viewer, drawings, manufacturing checks. |
| Multi-Agent CAD | [README](https://github.com/Pan-Chera/Multi-Agent-CAD): staged workflow, build123d, assembly technology preview. |
| AI-CAD | [README](https://github.com/ai-cad-labs/ai-cad): CadQuery workflow and saved artifacts. Claude Code is the documented tested default. |
| FreeCAD MCP | [README](https://github.com/neka-nat/freecad-mcp): FreeCAD addon and external MCP server. |
| OCP CAD Viewer | [README](https://github.com/bernhard-42/vscode-ocp-cad-viewer): supported libraries, measurements, selection, screenshots, debugging. |
| CQ-editor | [README](https://github.com/CadQuery/CQ-editor): desktop editor, graphical debugger, object inspector, exports. |
| ezdxf | [README](https://github.com/mozman/ezdxf): DXF operations and drawing/rendering add-ons. |
| CADGenBench | [README](https://github.com/huggingface/cadgenbench): drawing reconstruction, STEP editing, submission contract, metrics. |
| BenchCAD | [README](https://github.com/BenchCAD/BenchCAD-main): tasks, evaluator, dataset, CLI. |
| neuralCAD-Edit | [Project page](https://autodeskailab.github.io/neuralCAD-Edit/): editing requests, expert references, evaluation. |
| CADWorld | [Project page](https://cad-world.github.io/) and [paper](https://arxiv.org/abs/2609.16251): GUI interaction, saved-artifact evaluation. |

The current scope includes the software underneath agent workflows. New entries should fill a practical role; standalone paper curation has been removed. Older review notes remain in Git history.

## README entry points and example

Documentation and example links were checked against upstream READMEs on 2026-10-23. FreeCAD's wiki is linked from its official repository; automated access encounters an anti-bot page. CadQuery's examples page exceeds the browser fetch size limit; the URL is linked in its official README.

The [linear-stage example](../examples/linear-stage) was authored and executed by Codex in the repository-maintenance conversation using Python 3.12 and build123d 0.11.0. It includes 36 named parts, an 80 → 120 mm travel revision, and actual failures and repairs in the [run record](../examples/linear-stage/run). Geometry, saved STEP files, interface holes, nine carriage positions per variant, and a rebuild of the old configuration were checked. A separate cut-volume audit cross-checked the collision results after a coincident-cylinder issue appeared in the geometry comparison. Images are rendered from the saved STEP parts. Threads, bearing internals, and motor internals are simplified; checks cover geometric layout rather than mechanical performance.
