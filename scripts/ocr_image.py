#!/usr/bin/env python3
"""OCR Image CLI — 使用 RapidOCR 从图片中提取文字。

用法:
    python ocr_image.py <图片路径> [选项]

支持格式: .jpg, .jpeg, .png, .bmp, .tiff, .tif, .webp
语言模式: 中英混合(ch, 默认) / 纯英文(en)

示例:
    python ocr_image.py screenshot.png
    python ocr_image.py photo.jpg --format json
    python ocr_image.py ./images/ --format compact --lang en
"""

import argparse
import json
import sys
from pathlib import Path

# ── Windows UTF-8 编码 ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

# ── 支持的图片格式 ──────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

VERSION = "1.0.0"

# ── RapidOCR 引擎（懒加载单例）──────────────────────────────────────
_engine = None


def get_engine():
    """获取 RapidOCR 引擎实例（首次调用时初始化并下载模型）。"""
    global _engine
    if _engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            print(
                "错误: 未安装 rapidocr-onnxruntime。\n"
                "请运行: pip install rapidocr-onnxruntime\n"
                "或运行 install.bat 一键安装。",
                file=sys.stderr,
            )
            sys.exit(3)
        _engine = RapidOCR()
    return _engine


# ── 图片收集 ────────────────────────────────────────────────────────
def collect_images(path: Path) -> list[Path]:
    """收集待处理的图片文件。支持单文件或目录（非递归）。"""
    if path.is_file():
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(
                f"错误: 不支持的图片格式 '{path.suffix}'。\n"
                f"支持格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
                file=sys.stderr,
            )
            sys.exit(2)
        return [path]

    if path.is_dir():
        images = sorted(
            p for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not images:
            print(f"警告: 目录 '{path}' 中未找到支持的图片文件。", file=sys.stderr)
            sys.exit(1)
        return images

    print(f"错误: 文件或目录不存在: '{path}'", file=sys.stderr)
    sys.exit(2)


# ── 文字排序（上→下，左→右）────────────────────────────────────────
def sort_boxes(boxes: list) -> list:
    """按阅读顺序排列文本框：从上到下，同一行从左到右。"""
    # 使用每个框顶部 Y 坐标分组行（容差 = 框高度的一半）
    if not boxes:
        return boxes

    # 按 Y 坐标排序
    sorted_boxes = sorted(boxes, key=lambda b: (b[0][0][1], b[0][0][0]))
    return sorted_boxes


# ── 格式化输出 ──────────────────────────────────────────────────────
def format_compact(img_path: Path, blocks: list) -> str:
    """紧凑格式：适合回传模型，Token 效率最高。"""
    if not blocks:
        return f"[IMAGE: {img_path.name}]\n(图片中未检测到文字)\n[END IMAGE]"
    lines = [f"[IMAGE: {img_path.name}]"]
    for block in blocks:
        text = block[1]
        if text:
            lines.append(text)
    lines.append("[END IMAGE]")
    return "\n".join(lines)


def format_text(img_path: Path, blocks: list) -> str:
    """人类可读格式：含置信度和序号。"""
    if not blocks:
        return f"===== OCR: {img_path.name} =====\n(未检测到文字)\n===== END ====="
    lines = [f"===== OCR: {img_path.name} ====="]
    for i, block in enumerate(blocks, 1):
        text = block[1]
        confidence = float(block[2]) if len(block) > 2 else 0.0
        lines.append(f"  [{i}] conf={confidence:.3f} | {text}")
    lines.append(f"===== END: {img_path.name} =====")
    return "\n".join(lines)


def format_json(img_path: Path, blocks: list, elapsed: float = 0) -> str:
    """结构化 JSON 格式：适合程序消费。"""
    result = {
        "path": str(img_path.resolve()),
        "filename": img_path.name,
        "elapsed_seconds": round(elapsed, 3),
        "block_count": len(blocks),
        "text": "\n".join(block[1] for block in blocks if block[1]) if blocks else "",
        "blocks": [],
    }
    for block in blocks:
        result["blocks"].append({
            "box": block[0],
            "text": block[1],
            "confidence": round(float(block[2]), 4) if len(block) > 2 else 0.0,
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── 主逻辑 ──────────────────────────────────────────────────────────
def ocr_image(
    img_path: Path,
    engine,
    lang: str = "ch",
    box_threshold: float = 0.5,
) -> tuple[list | None, float]:
    """对单张图片执行 OCR。返回 (blocks, elapsed_seconds)。"""
    # RapidOCR 对语言的处理：默认模型支持中英文，无需特殊参数
    # engine() 返回 (result, elapse) — elapse 可能是 float 或 list[float]
    result, elapse = engine(str(img_path))

    # 统一 elapse 为 float（RapidOCR 有时返回列表）
    if isinstance(elapse, (list, tuple)):
        elapsed = sum(elapse)
    else:
        elapsed = float(elapse)

    if result is None:
        return None, elapsed

    # 按置信度过滤
    filtered = [b for b in result if len(b) > 2 and float(b[2]) >= box_threshold]

    if not filtered:
        return None, elapsed

    # 按阅读顺序排列
    sorted_result = sort_boxes(filtered)

    return sorted_result, elapsed


def main():
    parser = argparse.ArgumentParser(
        description="OCR Image — 使用 RapidOCR 从图片中提取中英文文字",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python ocr_image.py screenshot.png\n"
            "  python ocr_image.py photo.jpg --format json\n"
            "  python ocr_image.py ./images/ --format compact\n"
            "  python ocr_image.py receipt.png --box-threshold 0.3\n"
        ),
    )
    parser.add_argument(
        "image",
        help="图片文件路径或目录路径（支持 .jpg/.png/.bmp/.tiff/.webp）",
    )
    parser.add_argument(
        "--format",
        choices=["compact", "text", "json"],
        default="compact",
        help="输出格式: compact(模型友好,默认), text(人类阅读), json(结构化)",
    )
    parser.add_argument(
        "--lang",
        choices=["ch", "en"],
        default="ch",
        help="语言模式: ch=中英混合(默认), en=纯英文",
    )
    parser.add_argument(
        "--box-threshold",
        type=float,
        default=0.5,
        help="文本框置信度阈值 (0.0-1.0, 默认 0.5)。降低可召回更多文字但可能引入噪点",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ocr-image v{VERSION}",
    )

    args = parser.parse_args()

    # ── 初始化引擎 ──
    engine = get_engine()

    # ── 收集图片 ──
    img_path = Path(args.image)
    images = collect_images(img_path)

    # ── 逐张处理 ──
    all_failed = True
    for i, img in enumerate(images):
        if len(images) > 1:
            if i > 0:
                print()  # 多图时分隔
            print(f"--- [{i+1}/{len(images)}] ---", file=sys.stderr)

        try:
            blocks, elapsed = ocr_image(
                img,
                engine,
                lang=args.lang,
                box_threshold=args.box_threshold,
            )
        except Exception as exc:
            print(f"错误: 处理 '{img.name}' 时异常: {exc}", file=sys.stderr)
            continue

        all_failed = False

        # 格式化输出（到 stdout）
        if args.format == "compact":
            print(format_compact(img, blocks or []))
        elif args.format == "text":
            print(format_text(img, blocks or []))
        elif args.format == "json":
            print(format_json(img, blocks or [], elapsed))
        else:
            print(format_compact(img, blocks or []))

        # 耗时信息（到 stderr，不干扰正文输出）
        if elapsed:
            text_count = len(blocks) if blocks else 0
            print(
                f"  → {img.name}: {text_count} 段文字, 耗时 {elapsed:.2f}s",
                file=sys.stderr,
            )

    sys.exit(0 if not all_failed else 1)


if __name__ == "__main__":
    main()
