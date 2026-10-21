# ComfyUI_SaveJPEG

A minimal ComfyUI custom node that saves any input image as **JPEG** to the output directory. The input is an IMAGE tensor (not necessarily PNG — generated results, video frames, or processed images all work); the node encodes it as JPEG with selectable `jpg` / `jpeg` extension, configurable quality, and background fill for transparent pixels.

一个简单的 ComfyUI 自定义节点：把任意输入图像以 **JPEG 格式**保存到输出目录。输入是图像张量（不限于 PNG，生成结果、视频帧、处理后的图像均可），支持 `jpg` / `jpeg` 扩展名选择、质量调节、透明像素底色填充。

## 原理

ComfyUI 工作流内部图像是张量（IMAGE），本身没有“PNG / JPEG”的格式概念，格式在保存时才确定。
内置的 Save Image 节点固定输出 PNG，本插件提供同款操作、输出 **.jpg 或 .jpeg**（可下拉选择），并正确处理 JPEG 不支持透明通道的问题。

## 安装

1. 将整个 `ComfyUI_SaveJPEG` 文件夹复制到 ComfyUI 的 `custom_nodes/` 目录下；
2. 重启 ComfyUI。

无需额外依赖：仅使用 ComfyUI 自带的 `torch`、`numpy`、`Pillow`。

## 使用方法

最简单的连线：

```
Load Image  →  SaveJPEG
```

节点在节点库中的位置：`image` → `保存为 JPEG`（搜索 `SaveJPEG` 或 `JPEG` 亦可）。

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| images | IMAGE | - | 输入图像（张量，可批量） |
| quality | INT | 95 | JPEG 质量 1–100，越高越清晰、文件越大 |
| filename_prefix | STRING | `%yy%mm%dd_%hh%mi%ss` | 输出文件名前缀，保存到 ComfyUI `output/` 目录；默认值直接为日期+时间占位符（精确到秒），保存时替换为当前时间，见下方「文件名时间戳」 |
| background | 下拉 | white | 透明像素的填充底色（JPEG 不支持透明）：white / black |
| progressive | BOOL | false | 是否保存为渐进式 JPEG |
| extension | 下拉 | jpg | 输出文件扩展名：jpg / jpeg（格式均为 JPEG，仅扩展名不同） |
| preview | BOOL | true | 是否在 ComfyUI 界面显示本次保存的 JPEG 预览；关闭则只落盘、不显示预览 |

### 输出

- `images`：原样透传的 IMAGE（输入张量不做任何修改），可继续接入下游节点；
- 工作流运行后，右侧图片预览区会出现本次保存的 JPEG（`preview` 为 false 时只落盘、不显示预览），也可在 `output/` 目录直接查看文件。

批量输入会按序号分别命名（`前缀_00000_.jpg`、`前缀_00001_.jpg`…），与内置 Save Image 的命名规则一致。

### 文件名时间戳

`filename_prefix` 支持 `%` 开头的日期时间占位符，保存时替换为当前时间：

| 占位符 | 含义 | 示例（2026-10-21 02:45） |
|--------|------|--------------------------|
| %yyyy | 四位年份 | 2026 |
| %yy | 两位年份 | 26 |
| %mm | 两位月份 | 10 |
| %dd | 两位日期 | 21 |
| %hh | 两位小时（24 小时制） | 02 |
| %mi | 两位分钟 | 45 |
| %ss | 两位秒 | 30 |

节点默认的 `filename_prefix` 就是日期+时间占位符（`%yy%mm%dd_%hh%mi%ss`），不填前缀文字也会生成
`261021_024530_00000_.jpg` 这类按秒命名的文件，多次运行不会重名。

## 示例工作流

`examples/savejpeg_api_workflow.json` 为 API 格式的最小工作流：`Load Image → SaveJPEG`。
把该 JSON 拖入 ComfyUI 窗口（选择以 API 格式导入），并将 `Load Image` 节点中的 `example.png`
换成 `input/` 目录里实际存在的图片即可运行。

## 注意事项

- **透明通道**：JPEG 不支持 Alpha。带透明的图像会先合成到所选背景色上（默认白色），效果等同“抠底后铺白/黑底”。
- **元数据**：JPEG 不支持嵌入 prompt/workflow 元数据，保存的 `.jpg` 不携带工作流信息（内置 Save Image 的 PNG 才有）。
- 本插件只负责“保存为 JPEG”，不修改图像张量本身；如果不需要落盘、只想在流程内传递，直接用原有节点即可。

## 测试

未安装 ComfyUI 的环境也能运行核心逻辑自测：

```
python tests/test_core.py
```

覆盖：JPEG 编码、透明通道合成（白/黑底）、批量命名与输出目录写入、jpg/jpeg 扩展名、时间戳占位符、预览开关。

## License

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE).

This node is designed to run inside ComfyUI and imports ComfyUI's core `folder_paths` module (ComfyUI is licensed under GPL-3.0). The plugin's own code is provided under Apache 2.0, following the common practice of the ComfyUI custom-node ecosystem.

本节点运行于 ComfyUI 生态内，import 了 ComfyUI 核心的 `folder_paths` 模块（ComfyUI 为 GPL-3.0 授权）；插件自身代码以 Apache 2.0 授权，这是 ComfyUI 自定义节点生态的普遍做法。
