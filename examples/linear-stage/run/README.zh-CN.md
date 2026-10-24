# 执行记录

[English](README.md) · 简体中文 · [返回示例](../README.zh-CN.md)

建模 agent 为 **本次仓库维护对话中的 Codex**，执行日期为 2026-10-23；CAD 脚本在本机 Python 3.12、build123d 0.11.0 环境运行。[需求记录](../brief.md)整理了采用的要求与建模决策，并非另一个 agent 产品的对话转录。

每个编号 `.log` 保存命令输出和退出码；对应的 `.json` 保存 UTC 开始时间、命令耗时和代码哈希。命令中的本机解释器路径统一写作 `python`，异常栈中的工作目录缩写为 `<example>`。耗时仅指脚本执行，不代表 agent 完成设计的总耗时。

| 阶段 | 记录 | 结果 |
|---|---|---|
| 建立首版 80 mm 模型 | [01 日志](01-build-80.log)、[初始代码](snapshots/01-initial-model.py) | 导出中断：build123d 0.11.0 的 `Color` 没有 `to_tuple()` 方法。 |
| 修复颜色序列化 | [02 日志](02-build-80.log)、[代码](snapshots/02-export-fix-model.py) | 改为 `list(shape.color)`，导出 36 个零件。 |
| 检查几何与运动位置 | [03 日志](03-check-80.log)、[检查代码](snapshots/02-initial-check.py)、[失败版本](../generated/initial-80/assembly.step) | 发现 5 对固定零件干涉；9 个滑块位置均无动静零件干涉。 |
| 修正装配 | [04 建模](04-build-80-fixed.log)、[05 检查](05-check-80-fixed.log)、[代码](snapshots/04-clearance-fix-model.py) | 在底座增加电机避让槽，将两颗安装螺栓移位 0.8 mm，并在电机前盖补开轴孔。检查通过。 |
| 冻结基准 | [SHA-256 清单](frozen-80-sha256.json) | 在改参前记录通过检查的 80 mm 产物、建模及检查代码、原始配置。 |
| 将行程改为 120 mm | [06 建模](06-build-120.log)、[07 检查](07-check-120.log)、[配置](snapshots/06-config.json) | `travel` 从 80 改为 120；几何和 9 个位置的检查通过。 |
| 重建原尺寸 | [08 建模](08-rebuild-80.log)、[09 检查](09-check-rebuilt-80.log) | 最终建模代码仍能生成已接受的 80 mm 装配。 |
| 比较保存的几何 | [10 首次比较](10-compare-variants.log)、[初始比较代码](snapshots/10-initial-compare.py)、[12 修正后比较](12-compare-fixed.log) | 重合圆柱的布尔交集 `Common` 对平移后的电机轴返回空结果。双向相减确认其几何相同；修正比较方法后通过，未放宽体积阈值。 |
| 交叉核对干涉 | [13 核对](13-collision-audit.log) | 用布尔差集移除体积独立计算，两种行程的全部包围盒候选配对均与原干涉检查一致。 |
| 从 STEP 绘图 | [11 预览](11-render.log)、[15 最终绘图](15-render-labels.log) | 生成装配图、爆炸图和同尺度行程对比；调整对比视角以完整显示电机。 |

首版的五处干涉体积分别为：底座与电机 1680 mm³、底座与前盖 84 mm³、两颗螺栓头与前盖各 0.079145 mm³、前盖与轴 78.539816 mm³。修正后仍使用 0.00001 mm³ 阈值。

[最终改参检查](../generated/revision-checks.json)确认只有底座、两根导向杆和丝杆的几何发生改变；冻结文件保持不变，重新生成的每个 80 mm 零件均通过实体对称差比较。

图片来自实际导出的几何。爆炸偏移仅用于绘图，干涉检查使用装配位置。螺纹和轴承内部采用简化模型，运动检查覆盖 9 个采样位置，不代表连续行程证明。
