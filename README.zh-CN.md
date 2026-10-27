# Awesome Agentic CAD

用于机械 CAD 自动化的开源工具。

[English](README.md) · **简体中文** · [推荐工具](https://github.com/jason-wjs/awesome-agentic-cad/issues/new)

[![丝杆驱动直线滑台：装配、联动、分层爆炸和行程变更。](assets/stage-motion.gif)](examples/linear-stage-v2/README.zh-CN.md)

## 常见搭配

| 从哪里开始 | 工具与入口 |
|---|---|
| **已有 coding agent** | 给 agent 接入 [text-to-cad](https://www.texttocad.dev/install)，用自然语言创建和修改模型。完整的多 agent 工作流可看 [MAC](https://github.com/Pan-Chera/Multi-Agent-CAD#quick-start) 或 [AI-CAD](https://github.com/ai-cad-labs/ai-cad#get-exploring--quickstart)。 |
| **用 Python 建模** | 用 [CadQuery](https://cadquery.readthedocs.io/en/latest/examples.html) 或 [build123d](https://build123d.readthedocs.io/en/latest/introductory_examples.html) 建模，用 [OCP CAD Viewer](https://bernhard-42.github.io/ocp_viewer_docs/viewers/ocp_vscode/installation/) 查看几何。参见[滑台示例](examples/linear-stage-v2/README.zh-CN.md)。 |
| **在桌面 CAD 中工作** | [FreeCAD](https://wiki.freecad.org/Getting_started) + [FreeCAD MCP](https://github.com/neka-nat/freecad-mcp/blob/main/docs/installation.md)，让 agent 读取和操作打开的模型。 |

[建模](#建模) · [Agents 与接入工具](#agents-与接入工具) · [查看与调试](#查看与调试) · [图纸与文件交换](#图纸与文件交换) · [Benchmarks](#benchmarks)

## 建模

| 工具 | 用途 |
|---|---|
| [CadQuery](https://github.com/CadQuery/cadquery) | Python 参数化建模库，支持工作平面、实体操作、嵌套装配和 STEP/DXF 导出。<br>[文档](https://cadquery.readthedocs.io/en/latest/) · [示例](https://cadquery.readthedocs.io/en/latest/examples.html) |
| [build123d](https://github.com/gumyr/build123d) | 基于 Open CASCADE 的 Python 建模库，提供 builder 和代数式两套 API，用于创建草图、实体和装配。<br>[文档](https://build123d.readthedocs.io/en/latest/) · [示例](https://build123d.readthedocs.io/en/latest/introductory_examples.html) |
| [FreeCAD](https://github.com/FreeCAD/FreeCAD) | 带 Python API 的桌面参数化 CAD 软件，支持约束草图、建模历史和工程图。<br>[文档](https://wiki.freecad.org/Getting_started) |

## Agents 与接入工具

| 工具 | 用途 |
|---|---|
| [text-to-cad](https://github.com/earthtojake/text-to-cad) | 为 coding agent 提供的插件和 skills，包含 build123d 建模、本地查看器、工程图生成和制造检查。<br>[文档](https://www.texttocad.dev) · [安装](https://www.texttocad.dev/install) |
| [Multi-Agent CAD（MAC）](https://github.com/Pan-Chera/Multi-Agent-CAD) | 多个 agent 分工规划、建模、审查和修复，使用 build123d。装配功能目前为技术预览。<br>[文档](https://github.com/Pan-Chera/Multi-Agent-CAD/blob/main/multi_agent_cad/README.md) · [作品](https://github.com/Pan-Chera/Multi-Agent-CAD#part-gallery) |
| [AI-CAD](https://github.com/ai-cad-labs/ai-cad) | 在 Claude Code 中用多个 agent 设计 CadQuery 零件与装配，审查、修复模型，并保留运行记录。<br>[安装](https://github.com/ai-cad-labs/ai-cad#get-exploring--quickstart) · [示例](https://github.com/ai-cad-labs/ai-cad-example-projects) |
| [FreeCAD MCP](https://github.com/neka-nat/freecad-mcp) | 让 MCP 客户端读取和修改 FreeCAD 模型，并在 FreeCAD 中执行 Python 代码。<br>[安装](https://github.com/neka-nat/freecad-mcp/blob/main/docs/installation.md) · [示例](https://github.com/neka-nat/freecad-mcp/blob/main/docs/examples.md) |

## 查看与调试

| 工具 | 用途 |
|---|---|
| [OCP CAD Viewer](https://github.com/bernhard-42/vscode-ocp-cad-viewer) | 在 VS Code 中查看 CadQuery 和 build123d 模型，支持测量、对象选择、截图及可视化调试。<br>[文档](https://bernhard-42.github.io/ocp_viewer_docs/) · [示例](https://bernhard-42.github.io/ocp_viewer_docs/viewers/ocp_vscode/managers/#the-library-manager) |
| [CQ-editor](https://github.com/CadQuery/CQ-editor) | CadQuery 桌面编辑器，提供图形调试器、对象栈检查及 STEP/STL 导出。<br>[文档](https://github.com/CadQuery/CQ-editor/wiki/Usage) |

## 图纸与文件交换

| 工具 | 用途 |
|---|---|
| [ezdxf](https://github.com/mozman/ezdxf) | 用 Python 读写、修改 DXF 图纸，检查文件内容，并渲染为 SVG、PDF 等格式。<br>[文档](https://ezdxf.readthedocs.io/) |

CadQuery 和 build123d 支持 STEP 导入导出；FreeCAD 和 text-to-cad 还可生成工程图。

## Benchmarks

| Benchmark | 评测内容 |
|---|---|
| [CADGenBench](https://github.com/huggingface/cadgenbench) | 从工程图重建零件、修改 STEP 模型，按几何、接口和拓扑评分。 |
| [BenchCAD](https://github.com/BenchCAD/BenchCAD-main) | CAD 图像与代码问答、根据图像生成 CadQuery 代码、修改已有程序。 |
| [neuralCAD-Edit](https://autodeskailab.github.io/neuralCAD-Edit/) | 按多模态请求修改已有 CAD 模型，提供专家参考修改及人工评价。 |
| [CADWorld](https://cad-world.github.io/) | 操作 FreeCAD 完成 CAD 任务，检查保存的项目、约束和任务要求的输出文件。 |

配套项目 [CADsuite](https://github.com/jason-wjs/CADsuite) 用于测试 agent 在改参、按图建模和装配变更中的表现，目前为私有仓库。

## 参与贡献

欢迎推荐工具或提交 PR，中英文均可。只改一份 README 也可以，维护者会协助同步翻译。详见[贡献说明](CONTRIBUTING.md)和[来源记录](docs/curation-notes.md)。
