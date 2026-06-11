# ocr-image — 本地图片文字识别

基于 RapidOCR 的纯本地图片文字识别工具，为 Claude Code +deepseek 提供**非多模态模型的图片理解能力**。

## 解决的问题

当前使用的对话模型不支持多模态（无法直接读取图片），此技能提供桥接方案：

> 图片附件 → RapidOCR 提取文字 → 文字回传模型处理

所有处理完全本地运行，不上传任何数据。

## 安装

```bash
# 1. 安装依赖
pip install rapidocr-onnxruntime

# 或一键安装
scripts/install.bat
```

> 首次运行自动下载模型文件（~50MB）。

## 使用

```bash
# 基本用法
python scripts/ocr_image.py <图片路径> --format compact

# 中文+英文混合识别（默认）
python scripts/ocr_image.py screenshot.png

# 纯英文
python scripts/ocr_image.py receipt.jpg --lang en

# JSON 输出（含坐标和置信度）
python scripts/ocr_image.py photo.png --format json
```

## 输出格式

| 格式 | 用途 |
|------|------|
| `compact` | **默认**，Token 效率最高，适合回传模型 |
| `text` | 人类阅读，含置信度 |
| `json` | 结构化数据，含坐标 |

## 支持的图片

`.jpg` `.jpeg` `.png` `.bmp` `.tiff` `.webp`

## 已知局限

- 仅支持印刷体，手写识别率低
- 不支持竖排文字
- 模糊图片/超小字体识别率下降

## 隐私

100% 本地处理，无需联网。模型下载一次后离线使用。
