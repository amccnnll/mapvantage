#!/usr/bin/env python3
"""Generate single-page interactive visualization for all project imagery."""

from mapvantage.config import load_project_config
from mapvantage.html_gen import build_single_page_app
import sys
from pathlib import Path
import argparse

# Setup path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate single-page interactive visualization"
    )
    parser.add_argument(
        "--config",
        nargs="+",
        required=True,
        help="One or more project config files",
    )
    return parser.parse_args()


def main() -> int:
    """Generate visualization pages."""
    args = parse_args()

    # Group configs by project directory
    projects: dict[Path, list[Path]] = {}
    for config_arg in args.config:
        config_path = Path(config_arg).resolve()
        project_dir = config_path.parent
        if project_dir not in projects:
            projects[project_dir] = []
        projects[project_dir].append(config_path)

    # Generate pages for each project
    root_projects = []
    for project_dir, config_paths in projects.items():
        # Load first config to get project name and output dir
        first_cfg = load_project_config(config_paths[0])
        project_name = first_cfg.project_name
        output_dir = project_dir / first_cfg.output_dir

        if not output_dir.exists() or not any(output_dir.glob("*.png")):
            print(f"⚠ No images found for {project_name} in {output_dir}")
            continue

        # Generate single-page app
        page_title = project_name.replace("_", " ").title()
        output_path = project_dir / "web" / "index.html"

        try:
            build_single_page_app(
                project_title=page_title,
                images_dir=output_dir,
                project_name=project_name,
                output_path=output_path,
            )
            print(f"✓ Generated: {output_path.relative_to(ROOT)}")

            root_projects.append({
                "title": page_title,
                "href": str(output_path.relative_to(ROOT)).replace("\\", "/"),
            })
        except Exception as e:
            print(f"✗ Failed to generate {project_name}: {e}")
            return 1

    # Generate root index
    if root_projects:
        root_index_html = """<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>MapVantage</title>
	<style>
		* { box-sizing: border-box; }
		body {
			margin: 0;
			font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
			background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
			min-height: 100vh;
			color: #0f172a;
		}
		.shell { width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 32px 0 48px; }
		.hero { background: white; border: 1px solid rgba(15, 23, 42, 0.06); box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); border-radius: 12px; padding: 28px; margin-bottom: 24px; }
		h1 { margin: 0 0 12px; font-size: 2.5rem; font-weight: 700; }
		p { margin: 0; color: #64748b; line-height: 1.6; }
		.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; }
		.card { background: white; border: 1px solid rgba(15, 23, 42, 0.06); box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); border-radius: 12px; padding: 20px; text-decoration: none; color: inherit; transition: box-shadow 200ms; display: block; }
		.card:hover { box-shadow: 0 15px 40px rgba(15, 23, 42, 0.12); }
		.card h2 { margin: 0 0 12px; font-size: 1.25rem; }
		.card p { margin: 0; color: #64748b; }
		.button { display: inline-block; margin-top: 12px; padding: 10px 18px; background: #2563eb; color: white; border-radius: 8px; text-decoration: none; font-weight: 500; }
		@media (max-width: 760px) {
			.shell { width: calc(100vw - 20px); }
			h1 { font-size: 1.75rem; }
		}
	</style>
</head>
<body>
	<div class="shell">
		<section class="hero">
			<h1>MapVantage</h1>
			<p>Interactive tool for comparing historical orthophoto imagery. Select a project below to begin exploring.</p>
		</section>
		<div class="grid">
"""

        for project in root_projects:
            root_index_html += f"""			<a href="{project['href']}" class="card">
				<h2>{project['title']}</h2>
				<p>Explore historical imagery changes</p>
				<span class="button">Open →</span>
			</a>
"""

        root_index_html += """		</div>
	</div>
</body>
</html>"""

        root_path = ROOT / "index.html"
        root_path.write_text(root_index_html, encoding="utf-8")
        print(f"✓ Generated: index.html (root)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
