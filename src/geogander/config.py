from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class YearRequest:
    year: int
    service: str
    layer_id: int = 0


@dataclass
class ProjectConfig:
    project_name: str
    base_url: str
    endpoint: str
    bbox: str
    bbox_label: str
    crs: str
    image_size: str
    years: List[YearRequest]
    output_dir: str = "data/images"


def load_project_config(config_path: Path) -> ProjectConfig:
    """Load and validate a project YAML config used by scripts/fetch.py."""
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    api = raw.get("api", {})
    year_entries = raw.get("years", [])

    years = [
        YearRequest(
            year=int(item["year"]),
            service=str(item["service"]),
            layer_id=int(item.get("layer_id", api.get("default_layer_id", 0))),
        )
        for item in year_entries
    ]

    return ProjectConfig(
        project_name=str(raw.get("project_name", config_path.parent.name)),
        base_url=str(api["base_url"]),
        endpoint=str(api.get("endpoint", "/MapServer/export")),
        bbox=str(raw["bbox"]["coords"]),
        bbox_label=str(raw.get("bbox", {}).get("label", "")).strip(),
        crs=str(raw["crs"]),
        image_size=str(raw.get("image_size", "1600x1200")),
        years=years,
        output_dir=str(raw.get("output_dir", "data/images")),
    )
