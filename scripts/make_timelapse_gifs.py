#!/usr/bin/env python3
"""Create local per-site GIF timelapses with smooth crossfade transitions."""

from __future__ import annotations
from geogander.config import load_project_config

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
import yaml

# Setup path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass
class ImageAsset:
    year: int
    bbox_label: str
    path: Path


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "unknown"


def _parse_asset(path: Path) -> ImageAsset | None:
    # Expected stem format:
    # project__year__service__layerX__crs__bbox_label__bbox_coords__size
    parts = path.stem.split("__")
    if len(parts) != 8:
        return None

    _, year, _, layer_token, _, bbox_label, _, _ = parts
    if not year.isdigit() or not layer_token.startswith("layer"):
        return None

    return ImageAsset(year=int(year), bbox_label=bbox_label, path=path)


def _collect_site_assets(images_dir: Path) -> dict[str, list[ImageAsset]]:
    grouped: dict[str, dict[int, ImageAsset]] = {}

    for path in sorted(images_dir.glob("*.png")):
        asset = _parse_asset(path)
        if asset is None:
            continue

        if asset.bbox_label not in grouped:
            grouped[asset.bbox_label] = {}

        existing = grouped[asset.bbox_label].get(asset.year)
        # Keep the larger file if duplicate year variants exist.
        if existing is None or path.stat().st_size > existing.path.stat().st_size:
            grouped[asset.bbox_label][asset.year] = asset

    by_site: dict[str, list[ImageAsset]] = {}
    for site, per_year in grouped.items():
        by_site[site] = sorted(per_year.values(), key=lambda a: a.year)
    return by_site


def _load_rgb(path: Path, size: tuple[int, int] | None = None) -> Image.Image:
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        if size and rgb.size != size:
            rgb = rgb.resize(size, Image.Resampling.LANCZOS)
        return rgb


def _ease_in_out(t: float) -> float:
    # Smooth S-curve for less mechanical-looking transitions.
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _build_frames(
    assets: list[ImageAsset],
    transition_frames: int,
    transition_frame_ms: int,
    hold_ms: int,
    max_width: int,
) -> tuple[list[Image.Image], list[int]]:
    if len(assets) < 2:
        raise ValueError(
            "Need at least 2 yearly images to build a timelapse GIF.")

    first = _load_rgb(assets[0].path)
    if first.width > max_width:
        scale = max_width / first.width
        target_size = (max_width, max(1, round(first.height * scale)))
        first = first.resize(target_size, Image.Resampling.LANCZOS)
    else:
        target_size = first.size

    base_images = [first]
    for asset in assets[1:]:
        base_images.append(_load_rgb(asset.path, target_size))

    frames: list[Image.Image] = [base_images[0]]
    durations: list[int] = [hold_ms]

    for idx in range(len(base_images) - 1):
        a = base_images[idx]
        b = base_images[idx + 1]

        for step in range(1, transition_frames + 1):
            t = step / (transition_frames + 1)
            alpha = _ease_in_out(t)
            frames.append(Image.blend(a, b, alpha))
            durations.append(transition_frame_ms)

        frames.append(b)
        durations.append(hold_ms)

    return frames, durations


def _write_gif(output_path: Path, frames: list[Image.Image], durations: list[int]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def _prepare_gif_palette_frames(frames: list[Image.Image], colors: int) -> list[Image.Image]:
    # GIF supports <=256 colors; a lower palette can shrink files substantially.
    if not 2 <= colors <= 256:
        raise ValueError("--colors must be in range [2, 256]")

    return [
        frame.quantize(colors=colors, method=Image.Quantize.MEDIANCUT,
                       dither=Image.Dither.FLOYDSTEINBERG)
        for frame in frames
    ]


def _resolve_output_dir_from_config(config_path: Path) -> str:
    try:
        cfg = load_project_config(config_path)
        return cfg.output_dir
    except Exception:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return str(raw.get("output_dir", "data/images"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create local smooth-morph GIF timelapses from fetched imagery"
    )
    parser.add_argument(
        "--config",
        nargs="+",
        required=True,
        help="One or more config files used to resolve project output directories",
    )
    parser.add_argument(
        "--transition-frames",
        type=int,
        default=24,
        help="Crossfade in-between frames per year step (default: 24)",
    )
    parser.add_argument(
        "--transition-frame-ms",
        type=int,
        default=60,
        help="Duration of each in-between frame in ms (default: 60)",
    )
    parser.add_argument(
        "--hold-ms",
        type=int,
        default=700,
        help="How long to hold each real yearly frame in ms (default: 700)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=1200,
        help="Resize output GIF width cap (default: 1200)",
    )
    parser.add_argument(
        "--colors",
        type=int,
        default=128,
        help="GIF color palette size [2-256] (default: 128)",
    )
    parser.add_argument(
        "--output-dir",
        default="local_gifs",
        help="Project-relative output folder for GIFs (default: local_gifs)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.transition_frames < 1:
        raise ValueError("--transition-frames must be >= 1")

    projects: dict[Path, list[Path]] = {}
    for config_arg in args.config:
        config_path = Path(config_arg).resolve()
        projects.setdefault(config_path.parent, []).append(config_path)

    for project_dir, config_paths in projects.items():
        images_dir = project_dir / \
            _resolve_output_dir_from_config(config_paths[0])
        output_dir = project_dir / args.output_dir

        if not images_dir.exists():
            print(
                f"Skipping {project_dir.name}: images dir not found at {images_dir}")
            continue

        sites = _collect_site_assets(images_dir)
        if not sites:
            print(
                f"Skipping {project_dir.name}: no matching PNG assets found in {images_dir}")
            continue

        print(f"\nProject: {project_dir.name}")
        print(f"Images:  {images_dir}")
        print(f"Output:  {output_dir}")

        for site, assets in sorted(sites.items()):
            if len(assets) < 2:
                print(f"  - {site}: skipped (only {len(assets)} frame)")
                continue

            frames, durations = _build_frames(
                assets=assets,
                transition_frames=args.transition_frames,
                transition_frame_ms=args.transition_frame_ms,
                hold_ms=args.hold_ms,
                max_width=args.max_width,
            )
            palette_frames = _prepare_gif_palette_frames(
                frames, colors=args.colors)

            years = f"{assets[0].year}-{assets[-1].year}"
            output_name = f"{_slug(project_dir.name)}__{_slug(site)}__{years}.gif"
            output_path = output_dir / output_name
            _write_gif(output_path, palette_frames, durations)

            print(
                f"  - {site}: wrote {output_name} "
                f"({len(assets)} years, {len(frames)} total frames)"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
