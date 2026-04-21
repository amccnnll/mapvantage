#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mapvantage.html_gen import parse_image_asset


def _site_label(raw: str) -> str:
    return raw.replace("-", " ").replace("_", " ").title()


def _build_overlay_text(image_path: Path) -> str | None:
    asset = parse_image_asset(image_path)
    if asset is None:
        return None
    return f"{asset.year} | {_site_label(asset.bbox_label)} | SITCAN CC-BY-4.0"


def _load_font(image_width: int) -> ImageFont.ImageFont:
    # Scale text to image width; fall back to default bitmap font if needed.
    size = max(18, int(image_width * 0.018))
    for font_name in ("Arial.ttf", "Helvetica.ttc", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def annotate_image(image_path: Path, margin_px: int, dry_run: bool) -> bool:
    text = _build_overlay_text(image_path)
    if text is None:
        return False

    if dry_run:
        print(f"[DRY-RUN] {image_path.name}: {text}")
        return True

    with Image.open(image_path).convert("RGBA") as im:
        draw = ImageDraw.Draw(im)
        font = _load_font(im.width)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = max(margin_px, im.width - text_w - margin_px)
        y = margin_px

        # Draw subtle dark shadow so white text remains readable.
        shadow_offsets = [(-1, -1), (-1, 1), (1, -1), (1, 1), (0, 0)]
        for dx, dy in shadow_offsets:
            draw.text((x + dx, y + dy), text, fill=(0, 0, 0, 170), font=font)
        draw.text((x, y), text, fill=(255, 255, 255, 230), font=font)

        im.convert("RGB").save(image_path, format="PNG")

    print(f"Annotated: {image_path.name}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add top-right white overlay text to imagery.")
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("projects/cantabria_delta/data/images"),
        help="Directory containing PNG imagery files",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=20,
        help="Top/right text margin in pixels",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview overlay text without modifying files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    images_dir = args.images_dir.resolve()

    if not images_dir.exists():
        print(f"Images directory not found: {images_dir}")
        return 1

    pngs = sorted(images_dir.glob("*.png"))
    if not pngs:
        print(f"No PNG files found in: {images_dir}")
        return 1

    annotated = 0
    skipped = 0
    for image_path in pngs:
        if annotate_image(image_path, margin_px=args.margin, dry_run=args.dry_run):
            annotated += 1
        else:
            skipped += 1
            print(f"Skipped (unrecognized filename): {image_path.name}")

    print(f"Done. Annotated: {annotated}, Skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
