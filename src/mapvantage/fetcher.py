from pathlib import Path
from typing import Tuple

import requests


def parse_image_size(image_size: str) -> Tuple[int, int]:
    """Parse WIDTHxHEIGHT strings such as "1600x1200"."""
    parts = image_size.lower().split("x")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid image_size '{image_size}', expected WIDTHxHEIGHT")
    return int(parts[0]), int(parts[1])


def build_export_url(base_url: str, service: str, endpoint: str = "/MapServer/export") -> str:
    """Build ArcGIS export URL from base URL, service name, and endpoint."""
    return f"{base_url.rstrip('/')}/{service.strip('/')}{endpoint}"


def fetch_imagery(
        export_url: str,
        bbox: str,
        crs: str,
        image_size: str,
        output_path: Path,
        layer_id: int = 0,
        image_format: str = "png",
        timeout_seconds: int = 60,
) -> Path:
    """Fetch an image from an ArcGIS MapServer export endpoint and save it."""
    width, height = parse_image_size(image_size)
    sr_value = crs.replace(
        "EPSG:", "") if crs.upper().startswith("EPSG:") else crs

    params = {
        "bbox": bbox,
        "bboxSR": sr_value,
        "imageSR": sr_value,
        "size": f"{width},{height}",
        "layers": f"show:{layer_id}",
        "format": image_format,
        "transparent": "false",
        "f": "image",
    }

    response = requests.get(export_url, params=params, timeout=timeout_seconds)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path
