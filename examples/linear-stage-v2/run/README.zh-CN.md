# 运行记录 — 2026 年 10 月 23 日

[English](README.md) · [返回示例](../README.zh-CN.md)

Codex 将本轮工作分为建模、独立几何检查和视频制作，随后检查画面、整理中英文 README。输入为第一版滑台模型，以及完善机械细节、爆炸图、运动和行程对比的要求。下面的日志来自实际执行的命令；本页按工作内容归纳过程。

| 工作 | 记录 | 结果 |
|---|---|---|
| 首次生成精细版 80 mm 模型 | [model-01](model-01-initial-80.log) | 丝杆被导出为三个实体，需要让螺旋段与轴颈重叠连接。 |
| 修正连接并调查体积差异 | [model-02](model-02-connected-80.log)、[model-03](model-03-adaptive-80.log)、[model-04](model-04-adaptive-120.log) | 丝杆成为有效单实体；原生几何与 STEP 的体积积分仍有差异。 |
| 保留原生几何进行比较 | [model-05](model-05-native-proof-120.log)、[model-06](model-06-native-proof-80.log) | 附上丝杆原生 BREP，与 STEP 双向相减，结果均为空。 |
| 验证检查器 | [check-00](check-00-positive-controls.log)、[check-01](check-01-80.log)、[check-02](check-02-positive-controls-adaptive.log)、[check-03](check-03-positive-controls-adaptive.log)、[check-04](check-04-120.log) | 修复布尔结果 API 使用问题，并更新增加沉孔后的孔口高度预期。阳性对照能识别已知重叠，区分接触与穿透。 |
| 检查两种行程 | [check-05](check-05-80-report.json)、[check-06](check-06-120-report.json) | 两版均通过：59 个零件、各 15 个采样姿态、未发现干涉、端部间隙 6 mm。 |
| 独立重建与变更对比 | [model-07](model-07-rebuilt-80.log)、[check-07](check-07-revision-report.json) | 重建的 80 mm 模型全部 59 个零件几何一致；延长行程只改变四个零件的形状，其余 55 个保持原有局部几何。 |
| 静态图渲染 | [准备 80 mm](render-prepare-80-01.log)、[准备 120 mm](render-prepare-120-01.log)、[出图](render-views-01.log)、[v1 对比](render-baseline-01.log) | 使用 text-to-cad/cadgen 0.7.26，另存带材质和分层爆炸信息的展示模型。 |
| 运动视频 | [视频记录](../video/run/README.md) | 输出 24 秒 MP4 和 GIF，包含装配、联动、爆炸与同尺度行程对比。 |
| 10 月 24 日：首页 teaser | [转换记录](../video/run/10-teaser.json) | 将原有媒体改为一份 12 秒、2 倍速的 GIF，MP4 仅作本地中间文件。 |

命令旁的 JSON 文件记录时间和源码哈希；其中 `check-02` 从终端错误恢复，未记录时间和输入哈希。历史源码保存在 [snapshots](snapshots) 中，失败尝试也予以保留。几何检查另附输入文件哈希。[frozen-80-sha256.json](frozen-80-sha256.json)记录已验收的 80 mm 模型、检查器、配置及 CAD 输出，用于确认改参对比期间原版未被修改。

CAD 运行环境为 Python 3.12.14、build123d 0.11.0、cadquery-ocp-novtk 7.9.3.1.1。渲染在独立环境中使用 cadgen 0.7.26 和 build123d 0.11.1，通过 [cadgen_cli.py](../cadgen_cli.py)调用已安装的 Chrome。视频另附固定版本的依赖和输出哈希。
