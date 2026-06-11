---
name: ocr-image
description: Use when the user attaches an image file or references an image path that the model cannot read directly. Triggers on image attachments (.jpg/.jpeg/.png/.bmp/.tiff/.webp) in conversation, user requests like "read this image" / "OCR this" / "extract text from screenshot" / "what does this image say", or when the conversation includes local image file paths that need text extraction. Supports Chinese + English mixed text recognition via local RapidOCR engine (ONNX-based, no GPU required).
---

# OCR Image — 本地图片文字识别

## 概述

当模型无法直接读取图片内容（非多模态模型）时，通过本地 RapidOCR 引擎提取图片中的中英文文字，将结果回传模型进行后续处理。所有处理完全本地运行，不上传任何数据。

**核心流程**: 检测图片引用 → 运行 `ocr_image.py` → 读取 OCR 结果 → 基于文字内容回答用户

## 何时使用

**触发条件**（满足任一即触发）：
- 用户在对话中附加了图片文件（`.jpg`/`.png`/`.bmp`/`.tiff`/`.webp`）
- 用户说"读一下这张图"、"OCR 提取文字"、"图片里写了什么"
- 用户提供了本地图片路径并要求处理其中内容
- 对话上下文中出现无法直接查看的图片引用

**不适用场景**：
- PDF/DOCX/PPTX/XLSX 中的图片 → 使用 markitdown MCP 的 OCR 插件处理
- 用户要求"描述这张图片的画面"（非文字提取） → 需视觉模型
- 纯装饰性图片（无文字内容）

## 核心模式

### 关键：两种图片来源，定位方式不同

用户图片有**两种来源**，定位策略完全不同：

| 来源 | 特征 | 磁盘文件 | 定位方式 |
|------|------|----------|----------|
| 截图工具（Snipaste/微信等） | 文件名含 `ScreenShot_*`、`微信图片_*` | ✅ 有 | 按**创建时间**在 Temp 目录搜索 |
| 剪贴板粘贴（Ctrl+V） | 无文件名，显示 `original W×H` | ❌ 无 | 用 `PIL.ImageGrab.grabclipboard()` 从剪贴板提取 |

**判断依据**：看图片元信息。`[Image: original 2495x909]` 中的 "original" 意味着这是剪贴板粘贴，必须走剪贴板提取路线。

### 标准流程

**第 0 步 — 判断来源**
- 若有明确文件路径 → 直接跳到第 2 步
- 若为 `[Unsupported Image]` + `original W×H` → 剪贴板来源，执行第 1 步
- 若为 `[Unsupported Image]` 无元信息 → 先按时间搜 Temp 目录，搜不到再试剪贴板

**第 1 步 — 从剪贴板提取图片**（仅剪贴板来源）
```bash
rtk python -c "from PIL import ImageGrab; img = ImageGrab.grabclipboard(); img.save('C:/Users/pala/AppData/Local/Temp/_clipboard_image.png'); print(f'{img.size[0]}x{img.size[1]}')"
```
> 输出图片尺寸后，核对是否与 `[Image: original W×H]` 中的尺寸一致。一致则确认找对图片。
> 后续 OCR 使用 `C:\Users\pala\AppData\Local\Temp\_clipboard_image.png` 作为图片路径。

**第 2 步 — 执行 OCR**
```bash
rtk python "d:\AI\.claude\skills\ocr-image\scripts\ocr_image.py" "<图片绝对路径>" --format compact
```

**第 3 步 — 读结果并回答**
读取 stdout 中 `[IMAGE: ...]` 包裹的 OCR 文字，基于提取内容回答用户。

### 完整示例

用户: "告诉我图片里说了什么" `[Unsupported Image]` `[Image: original 2495x909]`

模型操作:
```bash
# 步骤1 — 从剪贴板提取
rtk python -c "from PIL import ImageGrab; img = ImageGrab.grabclipboard(); img.save('C:/Users/pala/AppData/Local/Temp/_clipboard_image.png'); print(f'{img.size[0]}x{img.size[1]}')"
# → 输出: 2495x909  ← 核对尺寸一致

# 步骤2 — OCR
rtk python "d:\AI\.claude\skills\ocr-image\scripts\ocr_image.py" "C:\Users\pala\AppData\Local\Temp\_clipboard_image.png" --format compact
```

## 快速参考

| 场景 | 命令模板 | 超时建议 |
|------|----------|----------|
| 剪贴板图片定位 | `python -c "from PIL import ImageGrab; img = ImageGrab.grabclipboard(); img.save(...); print(f'{img.size}')"` | 5s |
| 单图快速提取 | `ocr_image.py "path" --format compact` | 30s |
| 多图批量处理 | `ocr_image.py "dir/" --format compact` | 120s |
| 需要文字位置 | `ocr_image.py "path" --format json` | 30s |
| 低质量图片 | `ocr_image.py "path" --box-threshold 0.3` | 30s |
| 纯英文图片 | `ocr_image.py "path" --lang en` | 30s |
| 首次使用（需下载模型） | 同上，自动触发下载 | 120s |

**Python 路径**:
```
C:\Users\pala\AppData\Local\Python\pythoncore-3.14-64\python.exe
```

**脚本路径**:
```
d:\AI\.claude\skills\ocr-image\scripts\ocr_image.py
```

## 实现细节

### 输出格式对比

| 格式 | 用途 | 示例大小 | 使用时机 |
|------|------|----------|----------|
| `compact` | 回传模型 | 最小 | **默认选择**，大多数场景 |
| `text` | 人类审阅 | 中等 | 需要查看置信度时 |
| `json` | 程序处理 | 最大 | 需要坐标/结构化数据时 |

### 多图片处理

当用户提供多张图片时，逐张处理并在输出中用文件名区分：
```bash
rtk python "d:\AI\.claude\skills\ocr-image\scripts\ocr_image.py" "C:\Users\pala\Desktop\screenshots\" --format compact
```
> 目录模式下，脚本按文件名排序处理所有支持的图片格式。

### 退出码含义

| 退出码 | 含义 | 处理方式 |
|--------|------|----------|
| 0 | 全部成功 | 正常使用 stdout 结果 |
| 1 | 部分图片失败 | 检查 stderr 确定哪些失败，成功的仍可用 |
| 2 | 参数/文件错误 | 检查路径和格式，修正后重试 |
| 3 | 环境错误（RapidOCR 未安装） | 提示用户运行 install.bat |

### 超时策略

- 常规单图处理：设置 Bash timeout 为 **30000ms**（30秒）
- 首次使用或批量处理：设置 Bash timeout 为 **120000ms**（2分钟）
- 如果超时，提示用户图片可能过大或首次模型下载进行中

## 性能参考

| 图片类型 | 典型耗时 | 内存占用 |
|----------|----------|----------|
| 1080p 截图 | 1-3s | ~500MB |
| 4K 照片 | 3-8s | ~800MB |
| 手机拍照文档 | 2-5s | ~600MB |
| 首次运行（含模型下载） | 30-60s | ~1GB |

> RapidOCR 自动利用多核 CPU 加速。模型缓存到本地后，后续启动无需重复下载。

## 常见错误

| 错误 | 纠正 |
|------|------|
| **在磁盘上搜索剪贴板粘贴的图片** | 剪贴板图片**没有磁盘文件**，必须用 `ImageGrab.grabclipboard()` 提取 |
| **盲目搜 UUID `.tmp` 文件** | 这些是 VSCode 内部锁定的文件，无法读取；直接走剪贴板路线 |
| **不核对尺寸就 OCR** | 提取后核对尺寸与 `[Image: original W×H]` 一致，避免读了错误图片 |
| 试图直接读取图片内容 | 运行 ocr_image.py 代替 |
| 使用 `--format text` 浪费 Token | 默认用 `--format compact` |
| 忘记解析相对路径 | 始终使用绝对路径 |
| 不检查退出码 | 退出码 1 = 部分失败，检查 stderr |
| 对 PDF/文档运行 OCR | 使用 markitdown MCP — 此技能仅用于独立图片 |
| 首次运行超时 | 首次下载 ~50MB 模型，Bash timeout 设为 120000ms |

## 已知局限

1. **仅印刷体** — 手写文字识别准确率低，不保证效果
2. **水平文字** — 不支持竖排文字（如传统中文招牌）
3. **清晰度要求** — 文字高度 < 12px 或严重模糊的图片识别率下降
4. **复杂排版** — 表格、多栏混排的文字顺序可能不准确
5. **特殊字体** — 艺术字体、手写风格字体可能识别失败

## 隐私说明

所有 OCR 处理完全在本地进行。图片数据和识别结果**不会上传到任何外部服务器**。RapidOCR 模型文件下载一次后离线使用。
