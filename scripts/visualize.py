#!/usr/bin/env python3

from mapvantage.html_gen import (
    build_grid_page,
    build_opacity_page,
    build_project_index,
    build_root_index,
    build_site_index,
    build_slider_page,
    build_timelapse_page,
    collect_project_images,
    display_name,
    slugify,
)
from mapvantage.config import load_project_config
import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate static HTML comparison pages")
    parser.add_argument(
        "--config",
        nargs="+",
        required=True,
        help="One or more project config files, e.g. projects/cantabria_delta/config_oyambre.yaml",
    )
    parser.add_argument(
        "--type",
        default="slider,opacity,grid,timelapse",
        help="Comma-separated visualization types to generate",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_types = {item.strip()
                      for item in args.type.split(",") if item.strip()}
    project_payloads: dict[Path, dict[str, object]] = {}

    for config_arg in args.config:
        config_path = Path(config_arg).resolve()
        cfg = load_project_config(config_path)
        project_dir = config_path.parent
        images_dir = project_dir / cfg.output_dir
        images = collect_project_images(images_dir, cfg.project_name)
        if not images:
            raise FileNotFoundError(
                f"No images found for {cfg.project_name} in {images_dir}")

        site_slug = slugify(cfg.bbox_label or cfg.project_name)
        site_title = display_name(cfg.bbox_label or cfg.project_name)
        site_dir = project_dir / "web" / site_slug
        description = (
            f"{site_title} imagery in {cfg.crs} for bbox {cfg.bbox}. "
            f"Years: {', '.join(str(image.year) for image in images)}."
        )

        build_site_index(site_title, description, site_dir / "index.html")
        if "slider" in selected_types:
            build_slider_page(site_title, images, site_dir / "slider.html")
        if "opacity" in selected_types:
            build_opacity_page(site_title, images, site_dir / "opacity.html")
        if "grid" in selected_types:
            build_grid_page(site_title, images, site_dir / "grid.html")
        if "timelapse" in selected_types:
            build_timelapse_page(site_title, images,
                                 site_dir / "timelapse.html")

        if project_dir not in project_payloads:
            project_payloads[project_dir] = {
                "title": display_name(project_dir.name),
                "sites": [],
            }

        project_payloads[project_dir]["sites"].append(
            {
                "title": site_title,
                "description": description,
                "href": f"{site_slug}/index.html",
            }
        )

    root_projects: list[dict[str, str]] = []
    for project_dir, payload in project_payloads.items():
        build_project_index(
            payload["title"],
            payload["sites"],
            project_dir / "web" / "index.html",
        )
        root_projects.append(
            {
                "title": payload["title"],
                "description": f"Generated comparison pages for {payload['title']}.",
                "href": Path(project_dir.relative_to(ROOT)).as_posix() + "/web/index.html",
            }
        )

    build_root_index(root_projects, ROOT / "index.html")

    print("Generated pages:")
    for project in root_projects:
        print(f"- {project['title']}: {project['href']}")
    print(f"- Root GitHub Pages entry: {ROOT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
