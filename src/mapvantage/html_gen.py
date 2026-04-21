from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
import os
from pathlib import Path
from typing import Iterable


@dataclass
class ImageAsset:
    year: int
    service: str
    layer_id: int
    crs: str
    bbox_label: str
    bbox_coords: str
    image_size: str
    filename: str
    path: Path


def slugify(value: str) -> str:
    cleaned: list[str] = []
    last_was_sep = False
    for char in value.strip().lower():
        if char.isalnum():
            cleaned.append(char)
            last_was_sep = False
        elif not last_was_sep:
            cleaned.append("-")
            last_was_sep = True
    result = "".join(cleaned).strip("-")
    return result or "unknown"


def display_name(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def parse_image_asset(image_path: Path) -> ImageAsset | None:
    parts = image_path.stem.split("__")
    if len(parts) != 8:
        return None

    _, year, service, layer_token, crs, bbox_label, bbox_coords, image_size = parts
    if not year.isdigit() or not layer_token.startswith("layer"):
        return None

    return ImageAsset(
        year=int(year),
        service=service,
        layer_id=int(layer_token.replace("layer", "", 1)),
        crs=crs,
        bbox_label=bbox_label,
        bbox_coords=bbox_coords,
        image_size=image_size,
        filename=image_path.name,
        path=image_path,
    )


def collect_project_images(images_dir: Path, project_name: str) -> list[ImageAsset]:
    project_token = slugify(project_name)
    assets: list[ImageAsset] = []
    for image_path in sorted(images_dir.glob("*.png")):
        if not image_path.name.startswith(f"{project_token}__"):
            continue
        asset = parse_image_asset(image_path)
        if asset is not None:
            assets.append(asset)
    assets.sort(key=lambda item: item.year)
    return assets


def _relative_image_data(images: Iterable[ImageAsset], page_dir: Path) -> list[dict[str, str | int]]:
    records: list[dict[str, str | int]] = []
    for image in images:
        records.append(
            {
                "year": image.year,
                "service": image.service,
                "path": Path(os.path.relpath(image.path, page_dir)).as_posix(),
                "filename": image.filename,
            }
        )
    return records


def _write_html(output_path: Path, content: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _base_styles() -> str:
    return """
		:root {
			--paper: #ffffff;
			--ink: #0f172a;
			--muted: #64748b;
			--accent: #2563eb;
			--accent-soft: #dbeafe;
			--card: rgba(255, 255, 255, 0.97);
			--shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
		}
		* { box-sizing: border-box; }
		body {
			margin: 0;
			font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
			color: var(--ink);
			background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
			min-height: 100vh;
		}
		a { color: var(--accent); text-decoration: none; }
		a:hover { text-decoration: underline; }
		.shell {
			width: min(1180px, calc(100vw - 32px));
			margin: 0 auto;
			padding: 32px 0 48px;
		}
		.topbar {
			display: flex;
			justify-content: space-between;
			gap: 16px;
			align-items: center;
			margin-bottom: 24px;
			flex-wrap: wrap;
		}
		.crumb {
			font-size: 0.875rem;
			font-weight: 500;
			color: var(--muted);
			text-decoration: none;
		}
		.crumb:hover { color: var(--accent); }
		.hero, .panel, .card {
			background: var(--card);
			border: 1px solid rgba(15, 23, 42, 0.06);
			box-shadow: var(--shadow);
			border-radius: 12px;
		}
		.hero { padding: 28px; margin-bottom: 24px; }
		h1, h2, h3 { margin: 0 0 12px; color: var(--ink); }
		h1 { font-size: clamp(2rem, 4vw, 3.5rem); line-height: 1.1; font-weight: 700; }
		h2 { font-size: 1.5rem; font-weight: 600; }
		h3 { font-size: 1.125rem; font-weight: 600; }
		p { margin: 0; color: var(--muted); line-height: 1.6; }
		.meta {
			display: flex;
			gap: 12px;
			flex-wrap: wrap;
			margin-top: 16px;
		}
		.meta span {
			padding: 6px 12px;
			border-radius: 6px;
			background: var(--accent-soft);
			color: var(--accent);
			font-size: 0.875rem;
			font-weight: 500;
		}
		.panel { padding: 20px; }
		.button-row {
			display: flex;
			gap: 12px;
			flex-wrap: wrap;
			margin-top: 20px;
		}
		.button {
			display: inline-flex;
			align-items: center;
			justify-content: center;
			padding: 10px 18px;
			border-radius: 8px;
			background: var(--accent);
			color: white;
			text-decoration: none;
			border: 0;
			cursor: pointer;
			font: inherit;
			font-weight: 500;
			transition: background 200ms;
		}
		.button:hover { background: #1d4ed8; }
		.button.secondary {
			background: transparent;
			color: var(--ink);
			border: 1px solid rgba(15, 23, 42, 0.1);
		}
		.button.secondary:hover { background: #f1f5f9; }
		.grid {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
			gap: 18px;
		}
		.card { overflow: hidden; transition: box-shadow 200ms; }
		.card:hover { box-shadow: 0 15px 40px rgba(15, 23, 42, 0.12); }
		.card-body { padding: 18px; }
		.card img {
			width: 100%;
			display: block;
			aspect-ratio: 4 / 3;
			object-fit: cover;
			background: #f1f5f9;
		}
		.viewer {
			position: relative;
			border-radius: 12px;
			overflow: hidden;
			background: #f1f5f9;
			aspect-ratio: 4 / 3;
		}
		.viewer img {
			width: 100%;
			height: 100%;
			object-fit: contain;
			display: block;
		}
		.controls {
			display: grid;
			gap: 14px;
			margin-top: 18px;
		}
		.controls label {
			display: grid;
			gap: 8px;
			font-weight: 600;
			color: var(--ink);
		}
		.controls input[type=range] { width: 100%; cursor: pointer; }
		.caption {
			margin-top: 12px;
			font-size: 0.95rem;
			color: var(--muted);
		}
		@media (max-width: 760px) {
			.shell { width: min(100vw - 20px, 1180px); padding-top: 20px; }
			.hero, .panel { padding: 18px; }
		}
		"""


def build_site_index(site_title: str, description: str, output_path: Path) -> Path:
    content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>{escape(site_title)} | MapVantage</title>
	<style>{_base_styles()}</style>
</head>
<body>
	<div class=\"shell\">
		<div class=\"topbar\">
			<a class=\"crumb\" href=\"../index.html\">Project Index</a>

		</div>
		<section class=\"hero\">
			<h1>{escape(site_title)}</h1>
			<p>{escape(description)}</p>
			<div class=\"button-row\">
				<a class=\"button\" href=\"slider.html\">Slider Comparison</a>
				<a class=\"button secondary\" href=\"opacity.html\">Opacity Blend</a>
				<a class=\"button secondary\" href=\"grid.html\">Grid View</a>
				<a class=\"button secondary\" href=\"timelapse.html\">Timelapse</a>
			</div>
		</section>
	</div>
</body>
</html>
"""
    return _write_html(output_path, content)


def build_slider_page(site_title: str, images: list[ImageAsset], output_path: Path) -> Path:
    records = _relative_image_data(images, output_path.parent)
    before = records[0]
    after = records[-1]
    content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>{escape(site_title)} Slider | MapVantage</title>
	<style>
		{_base_styles()}
		.slider-overlay {{ position: absolute; inset: 0; overflow: hidden; }}
		.slider-overlay img {{ width: 100%; height: 100%; object-fit: contain; }}
		.divider {{ position: absolute; top: 0; bottom: 0; width: 3px; background: white; box-shadow: 0 0 0 1px rgba(0,0,0,0.15); }}
	</style>
</head>
<body>
	<div class=\"shell\">
		<div class=\"topbar\">
			<a class=\"crumb\" href=\"index.html\">Back to Site</a>

		</div>
		<section class=\"hero\">
			<h1>{escape(site_title)} Slider</h1>
			<p>Swipe between the earliest and latest imagery to check gross shoreline and channel changes.</p>
			<div class=\"meta\">
				<span>Before: {before['year']}</span>
				<span>After: {after['year']}</span>
			</div>
		</section>
		<section class=\"panel\">
			<div class=\"viewer\" id=\"slider-viewer\">
				<img src=\"{escape(str(before['path']))}\" alt=\"{before['year']}\">
				<div class=\"slider-overlay\" id=\"slider-overlay\">
					<img src=\"{escape(str(after['path']))}\" alt=\"{after['year']}\">
				</div>
				<div class=\"divider\" id=\"divider\"></div>
			</div>
			<div class=\"controls\">
				<label>Split position
					<input id=\"split\" type=\"range\" min=\"0\" max=\"100\" value=\"50\">
				</label>
			</div>
			<div class=\"caption\">{before['year']} on the left, {after['year']} on the right.</div>
		</section>
	</div>
	<script>
		const split = document.getElementById('split');
		const overlay = document.getElementById('slider-overlay');
		const divider = document.getElementById('divider');
		function render() {{
			const value = split.value;
			overlay.style.width = value + '%';
			divider.style.left = `calc(${{value}}% - 1px)`;
		}}
		split.addEventListener('input', render);
		render();
	</script>
</body>
</html>
"""
    return _write_html(output_path, content)


def build_opacity_page(site_title: str, images: list[ImageAsset], output_path: Path) -> Path:
    records = _relative_image_data(images, output_path.parent)
    base = records[0]
    overlay = records[-1]
    content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>{escape(site_title)} Opacity | MapVantage</title>
	<style>
		{_base_styles()}
		.stack img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }}
	</style>
</head>
<body>
	<div class=\"shell\">
		<div class=\"topbar\">
			<a class=\"crumb\" href=\"index.html\">Back to Site</a>

		</div>
		<section class=\"hero\">
			<h1>{escape(site_title)} Opacity Blend</h1>
			<p>Blend the earliest and latest imagery to inspect alignment and broad habitat change.</p>
			<div class=\"meta\">
				<span>Base: {base['year']}</span>
				<span>Overlay: {overlay['year']}</span>
			</div>
		</section>
		<section class=\"panel\">
			<div class=\"viewer stack\">
				<img src=\"{escape(str(base['path']))}\" alt=\"{base['year']}\">
				<img id=\"overlay\" src=\"{escape(str(overlay['path']))}\" alt=\"{overlay['year']}\" style=\"opacity:0.5\">
			</div>
			<div class=\"controls\">
				<label>Overlay opacity
					<input id=\"opacity\" type=\"range\" min=\"0\" max=\"100\" value=\"50\">
				</label>
			</div>
			<div class=\"caption\">Slide to change how strongly the {overlay['year']} layer sits on top of {base['year']}.</div>
		</section>
	</div>
	<script>
		const opacity = document.getElementById('opacity');
		const overlay = document.getElementById('overlay');
		function render() {{ overlay.style.opacity = opacity.value / 100; }}
		opacity.addEventListener('input', render);
		render();
	</script>
</body>
</html>
"""
    return _write_html(output_path, content)


def build_grid_page(site_title: str, images: list[ImageAsset], output_path: Path) -> Path:
    cards = []
    for record in _relative_image_data(images, output_path.parent):
        cards.append(
            f"""
						<article class=\"card\">
							<img src=\"{escape(str(record['path']))}\" alt=\"{record['year']}\">
							<div class=\"card-body\">
								<h3>{record['year']}</h3>
								<p>{escape(str(record['service']))}</p>
							</div>
						</article>
						"""
        )
    content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>{escape(site_title)} Grid | MapVantage</title>
	<style>{_base_styles()}</style>
</head>
<body>
	<div class=\"shell\">
		<div class=\"topbar\">
			<a class=\"crumb\" href=\"index.html\">Back to Site</a>

		</div>
		<section class=\"hero\">
			<h1>{escape(site_title)} Grid View</h1>
			<p>All fetched years side by side for quick visual scanning.</p>
		</section>
		<section class=\"grid\">{''.join(cards)}</section>
	</div>
</body>
</html>
"""
    return _write_html(output_path, content)


def build_timelapse_page(site_title: str, images: list[ImageAsset], output_path: Path) -> Path:
    records = _relative_image_data(images, output_path.parent)
    records_json = json.dumps(records)
    content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>{escape(site_title)} Timelapse | MapVantage</title>
	<style>{_base_styles()}</style>
</head>
<body>
	<div class=\"shell\">
		<div class=\"topbar\">
			<a class=\"crumb\" href=\"index.html\">Back to Site</a>

		</div>
		<section class=\"hero\">
			<h1>{escape(site_title)} Timelapse</h1>
			<p>Play through the fetched years in sequence.</p>
		</section>
		<section class=\"panel\">
			<div class=\"viewer\">
				<img id=\"frame\" src=\"{escape(str(records[0]['path']))}\" alt=\"Timelapse frame\">
			</div>
			<div class=\"controls\">
				<label>Year
					<input id=\"frame-range\" type=\"range\" min=\"0\" max=\"{len(records) - 1}\" value=\"0\">
				</label>
			</div>
			<div class=\"button-row\">
				<button id=\"play\" class=\"button\" type=\"button\">Play</button>
				<button id=\"pause\" class=\"button secondary\" type=\"button\">Pause</button>
			</div>
			<div class=\"caption\" id=\"caption\"></div>
		</section>
	</div>
	<script>
		const records = {records_json};
		const frame = document.getElementById('frame');
		const range = document.getElementById('frame-range');
		const caption = document.getElementById('caption');
		let timer = null;
		function render() {{
			const item = records[Number(range.value)];
			frame.src = item.path;
			caption.textContent = `${{item.year}} — ${{item.service}}`;
		}}
		function start() {{
			if (timer !== null) return;
			timer = window.setInterval(() => {{
				range.value = (Number(range.value) + 1) % records.length;
				render();
			}}, 1200);
		}}
		function stop() {{
			if (timer !== null) {{
				window.clearInterval(timer);
				timer = null;
			}}
		}}
		range.addEventListener('input', render);
		document.getElementById('play').addEventListener('click', start);
		document.getElementById('pause').addEventListener('click', stop);
		render();
	</script>
</body>
</html>
"""
    return _write_html(output_path, content)


def build_project_index(project_title: str, sites: list[dict[str, str]], output_path: Path) -> Path:
    cards = []
    for site in sites:
        cards.append(
            f"""
						<article class=\"card\">
							<div class=\"card-body\">
								<h3>{escape(site['title'])}</h3>
								<p>{escape(site['description'])}</p>
								<div class=\"button-row\">
									<a class=\"button\" href=\"{escape(site['href'])}\">Open Site</a>
								</div>
							</div>
						</article>
						"""
        )
    content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>{escape(project_title)} | MapVantage</title>
	<style>{_base_styles()}</style>
</head>
<body>
	<div class=\"shell\">

		<section class=\"hero\">
			<h1>{escape(project_title)}</h1>
			<p>Site-level comparison pages generated from current fetch outputs.</p>
		</section>
		<section class=\"grid\">{''.join(cards)}</section>
	</div>
</body>
</html>
"""
    return _write_html(output_path, content)


def build_root_index(projects: list[dict[str, str]], output_path: Path) -> Path:
    links = []
    for project in projects:
        links.append(
            f"""
						<article class=\"card\">
							<div class=\"card-body\">
								<h3>{escape(project['title'])}</h3>
								<p>{escape(project['description'])}</p>
								<div class=\"button-row\">
									<a class=\"button\" href=\"{escape(project['href'])}\">Open Project</a>
								</div>
							</div>
						</article>
						"""
        )
    content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\">
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
	<title>MapVantage</title>
	<style>{_base_styles()}</style>
</head>
<body>
	<div class=\"shell\">
		<section class=\"hero\">
			<h1>MapVantage</h1>
			<p>Interactive visual comparison pages for fetched historical imagery. This root index is intended to work when GitHub Pages is published from the <code>main</code> branch root.</p>
		</section>
		<section class=\"grid\">{''.join(links)}</section>
	</div>
</body>
</html>
"""
    return _write_html(output_path, content)
