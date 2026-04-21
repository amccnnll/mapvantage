#!/usr/bin/env python3

from geogander.fetcher import build_export_url, fetch_imagery
from geogander.config import load_project_config
import argparse
import sys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _slug(value: str) -> str:
    """Create filesystem-safe ASCII-ish tokens for output filenames."""
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip())
    return cleaned.strip("-").lower() or "unknown"


def _bbox_token(bbox: str) -> str:
    return _slug(bbox.replace(",", "_"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch imagery from ArcGIS-style endpoints")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to project YAML config, e.g. projects/cantabria_delta/config.yaml",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    cfg = load_project_config(config_path)

    project_dir = config_path.parent
    output_dir = project_dir / cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Project: {cfg.project_name}")
    print(f"Output:  {output_dir}")
    print(f"BBox:    {cfg.bbox}")
    print(f"CRS:     {cfg.crs}")

    for item in cfg.years:
        export_url = build_export_url(cfg.base_url, item.service, cfg.endpoint)
        project_token = _slug(cfg.project_name)
        service_token = _slug(item.service)
        crs_token = _slug(cfg.crs)
        bbox_label_token = _slug(cfg.bbox_label) if cfg.bbox_label else "bbox"
        bbox_coords_token = _bbox_token(cfg.bbox)
        size_token = _slug(cfg.image_size)
        output_name = (
            f"{project_token}__{item.year}__{service_token}"
            f"__layer{item.layer_id}__{crs_token}"
            f"__{bbox_label_token}__{bbox_coords_token}__{size_token}.png"
        )
        output_file = output_dir / output_name
        print(f"Fetching {item.year} from {item.service}...")

        fetch_imagery(
            export_url=export_url,
            bbox=cfg.bbox,
            crs=cfg.crs,
            image_size=cfg.image_size,
            output_path=output_file,
            layer_id=item.layer_id,
            image_format="png",
        )

        print(f"Saved: {output_file}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
