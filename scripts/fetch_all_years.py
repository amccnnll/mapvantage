#!/usr/bin/env python3
import re
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from mapvantage.config import load_project_config
from mapvantage.fetcher import fetch_imagery

AVAILABLE_YEARS = [
    (1946, "Ortofoto_45_46"),
    (1957, "Ortofoto_56_57"),
    (1980, "Ortofoto_80_90"),
    (1986, "Ortofoto_77_86"),
    (2001, "Ortofoto_2001"),
    (2002, "Ortofoto_2002"),
    (2005, "Ortofoto_2005"),
    (2007, "Ortofoto_2007"),
    (2010, "Ortofoto_2010"),
    (2014, "Ortofoto_2014"),
    (2017, "Ortofoto_2017"),
    (2018, "Ortofoto_2018"),
    (2020, "Ortofoto_2020"),
    (2023, "Ortofoto_2023"),
    (2024, "Ortofoto_2024"),
    (2025, "Ortofoto_2025"),
]

def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

def _bbox_token(bbox: str) -> str:
    return bbox.replace(",", "-")

def fetch_for_site(site_name: str, config_path: Path):
    print(f"\n{'=' * 60}\nFetching {site_name} imagery...\n{'=' * 60}")
    cfg = load_project_config(config_path)
    project_token = _slug(cfg.project_name)
    crs_token = _slug(cfg.crs)
    bbox_label_token = _slug(cfg.bbox_label) if cfg.bbox_label else "bbox"
    bbox_coords_token = _bbox_token(cfg.bbox)
    size_token = _slug(cfg.image_size)
    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    fetched = 0
    failed = 0
    
    for year, service in AVAILABLE_YEARS:
        try:
            print(f"  {service} ({year})...", end=" ", flush=True)
            export_url = f"{cfg.base_url}/{service}{cfg.endpoint}"
            service_token = _slug(service)
            output_name = f"{project_token}__{year}__{service_token}__layer0__{crs_token}__{bbox_label_token}__{bbox_coords_token}__{size_token}.png"
            output_file = output_dir / output_name
            fetch_imagery(export_url=export_url, bbox=cfg.bbox, crs=cfg.crs, image_size=cfg.image_size, output_path=output_file, layer_id=0, image_format="png", timeout_seconds=60)
            print("✓")
            fetched += 1
        except Exception as e:
            print(f"✗ {e}")
            failed += 1
    
    print(f"  Fetched: {fetched}, Failed: {failed}")
    return fetched, failed

if __name__ == "__main__":
    config_dir = Path("projects/cantabria_delta")
    total_fetched = total_failed = 0
    f, fa = fetch_for_site("Oyambre", config_dir / "config_oyambre.yaml")
    total_fetched += f; total_failed += fa
    f, fa = fetch_for_site("Santander", config_dir / "config_santander.yaml")
    total_fetched += f; total_failed += fa
    print(f"\n{'=' * 60}\nSummary: {total_fetched} fetched, {total_failed} failed\n{'=' * 60}")
