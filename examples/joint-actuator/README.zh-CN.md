# 中空关节模组

[English](README.md) · **简体中文** · [工具列表](../../README.zh-CN.md)

根据一张剖切参考图，用 build123d 建立的无框电机与谐波减速器模型。下表尺寸为本示例选定的参数。

![电机、减速器和输出轴承的剖切图。](generated/cutaway.png)

[Ø20 STEP](generated/bore-20/assembly.step) · [Ø30 STEP](generated/bore-30/assembly.step) · [建模代码](model.py) · [建模与检查记录](run/README.zh-CN.md)

## 装配结构

铜绕组环绕分段转子。减速器包含椭圆波发生器、薄壁柔轮和刚轮，另有轴承套圈、滚子、编码器板和内六角紧固件。

![关节模组沿轴向展开的爆炸图。](generated/exploded.png)

柔轮和刚轮分别有 80 齿和 82 齿。齿形经过简化，未变形的零件之间留有间隙，未模拟柔轮变形和齿面接触。剖切图和爆炸图使用完整装配中的同一套 CAD 零件。

## 扩大中空孔径

![同一比例下的 20 mm 和 30 mm 通孔对比。](generated/bore-comparison.png)

| 尺寸 | 初始模型 | 修改后 |
|---|---:|---:|
| 中空孔径 | 20 mm | 30 mm |
| 壳体最大外径 | 110 mm | 不变 |
| 总长 | 96 mm | 不变 |
| 后端安装孔 | Ø96 mm 分度圆上 8 × Ø4.4 | 不变 |
| 前端安装孔 | Ø80 mm 分度圆上 8 × Ø4.4 | 不变 |

两份配置（[20 mm](config-20.json)、[30 mm](config-30.json)）仅孔径不同。随之变化的六个零件是后盖、转子筒、中空轴、波发生器、柔轮和输出法兰。

[检查程序](check.py)读取导出的 STEP 几何。两个版本均通过检查：56 个命名零件、254 个有效实体，通孔畅通，未检出干涉。[改参报告](run/revision.json)确认了外形尺寸和安装接口不变。

## 运行

使用 Python 3.12 和 build123d 0.11.0，在本目录下执行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python model.py --config config-20.json --output generated/bore-20
python model.py --config config-30.json --output generated/bore-30
python check.py --self-test
python check.py generated/bore-20 generated/bore-30 --output run/check.json
```

仓库中保留完整装配和剖切 STEP 文件。上述命令会重新生成检查与渲染所需的单独零件文件。GIF 制作见[动画复现说明](video/README.md)。此前的[直线滑台示例](../linear-stage-v2/README.zh-CN.md)仍保留在仓库中。
