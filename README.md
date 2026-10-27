# Awesome Agentic CAD

Open-source tools for automating mechanical CAD with AI agents.

**English** · [简体中文](README.zh-CN.md) · [Suggest a tool](https://github.com/jason-wjs/awesome-agentic-cad/issues/new)

[![A screw-driven linear stage: assembly, motion, exploded view, and travel revision.](assets/stage-motion.gif)](examples/linear-stage-v2)

## Common setups

| Start with | Tools & first steps |
|---|---|
| **Your coding agent** | Add [text-to-cad](https://www.texttocad.dev/install) to create and edit models from natural language. For full multi-agent workflows, see [MAC](https://github.com/Pan-Chera/Multi-Agent-CAD#quick-start) or [AI-CAD](https://github.com/ai-cad-labs/ai-cad#get-exploring--quickstart). |
| **Python scripts** | Model with [CadQuery](https://cadquery.readthedocs.io/en/latest/examples.html) or [build123d](https://build123d.readthedocs.io/en/latest/introductory_examples.html), and inspect the result in [OCP CAD Viewer](https://bernhard-42.github.io/ocp_viewer_docs/viewers/ocp_vscode/installation/). See the [linear stage example](examples/linear-stage-v2). |
| **Desktop CAD** | [FreeCAD](https://wiki.freecad.org/Getting_started) + [FreeCAD MCP](https://github.com/neka-nat/freecad-mcp/blob/main/docs/installation.md) to let an agent inspect and work on an open model. |

[Modeling](#modeling) · [Agents & integrations](#agents--integrations) · [Viewing & debugging](#viewing--debugging) · [Drawings & file exchange](#drawings--file-exchange) · [Benchmarks](#benchmarks)

## Modeling

| Tool | What it does |
|---|---|
| [CadQuery](https://github.com/CadQuery/cadquery) | Python parametric modeling with workplanes, solid operations, nested assemblies, and STEP/DXF export.<br>[Docs](https://cadquery.readthedocs.io/en/latest/) · [Examples](https://cadquery.readthedocs.io/en/latest/examples.html) |
| [build123d](https://github.com/gumyr/build123d) | Open CASCADE-based Python modeling for sketches, solids, and assemblies, with builder and algebraic APIs.<br>[Docs](https://build123d.readthedocs.io/en/latest/) · [Examples](https://build123d.readthedocs.io/en/latest/introductory_examples.html) |
| [FreeCAD](https://github.com/FreeCAD/FreeCAD) | A desktop parametric modeler with a Python API, constrained sketches, model history, and engineering drawings.<br>[Docs](https://wiki.freecad.org/Getting_started) |

## Agents & integrations

| Tool | What it does |
|---|---|
| [text-to-cad](https://github.com/earthtojake/text-to-cad) | Plugins and skills that give coding agents build123d modeling, a local viewer, drawing generation, and manufacturing checks.<br>[Docs](https://www.texttocad.dev) · [Setup](https://www.texttocad.dev/install) |
| [Multi-Agent CAD (MAC)](https://github.com/Pan-Chera/Multi-Agent-CAD) | Plans, builds, reviews, and repairs CAD models with multiple agents. Uses build123d; assembly support is in technology preview.<br>[Docs](https://github.com/Pan-Chera/Multi-Agent-CAD/blob/main/multi_agent_cad/README.md) · [Gallery](https://github.com/Pan-Chera/Multi-Agent-CAD#part-gallery) |
| [AI-CAD](https://github.com/ai-cad-labs/ai-cad) | Uses multiple agents to design parts and assemblies in CadQuery, review models, and fix errors. Runs on Claude Code and keeps a run history.<br>[Setup](https://github.com/ai-cad-labs/ai-cad#get-exploring--quickstart) · [Examples](https://github.com/ai-cad-labs/ai-cad-example-projects) |
| [FreeCAD MCP](https://github.com/neka-nat/freecad-mcp) | Connects an MCP client to FreeCAD for document inspection, modeling, and Python execution.<br>[Setup](https://github.com/neka-nat/freecad-mcp/blob/main/docs/installation.md) · [Examples](https://github.com/neka-nat/freecad-mcp/blob/main/docs/examples.md) |

## Viewing & debugging

| Tool | What it does |
|---|---|
| [OCP CAD Viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer) | Shows CadQuery and build123d models in VS Code, with measurements, object selection, screenshots, and visual debugging.<br>[Docs](https://bernhard-42.github.io/ocp_viewer_docs/) · [Examples](https://bernhard-42.github.io/ocp_viewer_docs/viewers/ocp_vscode/managers/#the-library-manager) |
| [CQ-editor](https://github.com/CadQuery/CQ-editor) | A desktop editor for CadQuery with a graphical debugger, object-stack inspection, and STEP/STL export.<br>[Docs](https://github.com/CadQuery/CQ-editor/wiki/Usage) |

## Drawings & file exchange

| Tool | What it does |
|---|---|
| [ezdxf](https://github.com/mozman/ezdxf) | Reads, edits, and writes DXF drawings in Python, with tools for inspecting files and rendering SVG and PDF.<br>[Docs](https://ezdxf.readthedocs.io/) |

CadQuery and build123d support STEP import/export; FreeCAD and text-to-cad also generate engineering drawings.

## Benchmarks

| Benchmark | What it tests |
|---|---|
| [CADGenBench](https://github.com/huggingface/cadgenbench) | Reconstructing parts from engineering drawings and editing STEP models. Scores geometry, interfaces, and topology. |
| [BenchCAD](https://github.com/BenchCAD/BenchCAD-main) | Visual and code-based CAD questions, image-to-CadQuery generation, and program editing. |
| [neuralCAD-Edit](https://autodeskailab.github.io/neuralCAD-Edit/) | Editing existing CAD models from multimodal requests, with expert reference edits and human evaluation. |
| [CADWorld](https://cad-world.github.io/) | Operating FreeCAD to complete CAD tasks. Checks saved projects, constraints, and task outputs. |

[CADsuite](https://github.com/jason-wjs/CADsuite) is our companion project for testing agents on parameter changes, modeling from drawings, and assembly revisions. The repository is currently private.

## Contributing

Tool suggestions and pull requests are welcome in English or Chinese. You can edit either README; maintainers can help sync the translation. See the [contribution guide](CONTRIBUTING.md) and [source notes](docs/curation-notes.md).
