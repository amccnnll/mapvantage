from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
from typing import Iterable

from PIL import Image


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
	<title>{escape(site_title)} | Geogander</title>
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
	<title>{escape(site_title)} Slider | Geogander</title>
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
	<title>{escape(site_title)} Opacity | Geogander</title>
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
	<title>{escape(site_title)} Grid | Geogander</title>
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
	<title>{escape(site_title)} Timelapse | Geogander</title>
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
	<title>{escape(project_title)} | Geogander</title>
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
	<title>Geogander</title>
	<style>{_base_styles()}</style>
</head>
<body>
	<div class=\"shell\">
		<section class=\"hero\">
			<h1>Geogander</h1>
			<p>Interactive visual comparison pages for fetched historical imagery. This root index is intended to work when GitHub Pages is published from the <code>main</code> branch root.</p>
		</section>
		<section class=\"grid\">{''.join(links)}</section>
	</div>
</body>
</html>
"""
    return _write_html(output_path, content)


def collect_images_by_site(images_dir: Path, project_name: str) -> dict[str, list[ImageAsset]]:
    """Collect images and organize by bbox_label (site)."""
    sites: dict[str, list[ImageAsset]] = {}

    for image_path in sorted(images_dir.glob("*.png")):
        asset = parse_image_asset(image_path)
        if asset is not None:
            if asset.bbox_label not in sites:
                sites[asset.bbox_label] = []
            sites[asset.bbox_label].append(asset)

    # Sort by year within each site
    for site_images in sites.values():
        site_images.sort(key=lambda item: item.year)

    return sites


def _build_timelapse_derivatives(
	sites: dict[str, list[ImageAsset]],
	page_dir: Path,
	max_width: int = 1280,
	quality: int = 72,
) -> dict[Path, str]:
	"""Create lighter JPEG derivatives for timelapse playback."""
	derivatives: dict[Path, str] = {}
	output_dir = page_dir / "images" / "timelapse"
	output_dir.mkdir(parents=True, exist_ok=True)

	for site_images in sites.values():
		for img in site_images:
			source = img.path.resolve()
			target = output_dir / f"{img.path.stem}__tl.jpg"

			rebuild = not target.exists() or target.stat().st_mtime < img.path.stat().st_mtime
			if rebuild:
				with Image.open(img.path) as source_image:
					source_image = source_image.convert("RGB")
					width, height = source_image.size
					if width > max_width:
						scaled_height = max(1, round(height * (max_width / width)))
						source_image = source_image.resize((max_width, scaled_height), Image.Resampling.LANCZOS)
					source_image.save(target, format="JPEG", quality=quality, optimize=True, progressive=True)

			rel = Path(target.relative_to(page_dir)).as_posix()
			derivatives[source] = rel

	return derivatives


def _generate_image_data(
	sites: dict[str, list[ImageAsset]],
	base_dir: Path,
	timelapse_derivatives: dict[Path, str] | None = None,
) -> str:
    """Generate JSON data for all images."""
    data: dict[str, dict[str, list]] = {}
	tl_derivatives = timelapse_derivatives or {}

    for site_slug, images in sites.items():
        site_key = site_slug.title()  # Display name
        data[site_key] = {"images": []}

        for img in images:
            rel_path = str(img.path.relative_to(
                base_dir, walk_up=True)).replace("\\", "/")
			timelapse_path = tl_derivatives.get(img.path.resolve(), rel_path)
            data[site_key]["images"].append({
                "year": img.year,
                "service": img.service,
                "path": rel_path,
				"timelapse_path": timelapse_path,
                "site": site_slug,
            })

    return json.dumps(data)


def build_single_page_app(
    project_title: str,
    images_dir: Path,
    project_name: str,
    output_path: Path,
) -> Path:
    """Generate a single-page interactive app for comparing imagery."""

    # Collect images organized by site
    sites = collect_images_by_site(images_dir, project_name)

    if not sites:
        raise ValueError(f"No images found in {images_dir}")

	timelapse_derivatives = _build_timelapse_derivatives(sites, output_path.parent)

	# Generate image data as JSON
	image_data = _generate_image_data(sites, output_path.parent, timelapse_derivatives)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{escape(project_title)} | Geogander</title>
	<style>
		:root {{
			--paper: #ffffff;
			--ink: #0f172a;
			--muted: #64748b;
			--accent: #2563eb;
			--accent-soft: #dbeafe;
			--card: rgba(255, 255, 255, 0.97);
			--shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
		}}
		* {{ box-sizing: border-box; }}
		body {{
			margin: 0;
			font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
			color: var(--ink);
			background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
			min-height: 100vh;
		}}
		.shell {{ width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 32px 0 48px; }}
		.hero {{ background: var(--card); border: 1px solid rgba(15, 23, 42, 0.06); box-shadow: var(--shadow); border-radius: 12px; padding: 28px; margin-bottom: 24px; }}
		h1 {{ margin: 0 0 12px; color: var(--ink); font-size: 2.5rem; font-weight: 700; }}
		p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
		.controls-panel {{ background: var(--card); border: 1px solid rgba(15, 23, 42, 0.06); box-shadow: var(--shadow); border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
		.control-group {{ margin-bottom: 16px; }}
		.control-label {{ display: block; font-weight: 600; margin-bottom: 8px; font-size: 0.875rem; }}
		.control-input {{ width: 100%; padding: 10px 12px; border: 1px solid rgba(15, 23, 42, 0.15); border-radius: 6px; font: inherit; }}
		.button-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0; }}
		.button {{ padding: 10px 18px; border: none; border-radius: 8px; background: var(--accent); color: white; cursor: pointer; font-weight: 500; transition: all 200ms; }}
		.button:hover {{ background: #1d4ed8; }}
		.button.secondary {{ background: transparent; color: var(--ink); border: 1px solid rgba(15, 23, 42, 0.1); }}
		.button.secondary.active {{ background: var(--accent-soft); color: var(--accent); border-color: var(--accent); }}
		.viewer-panel {{ background: var(--card); border: 1px solid rgba(15, 23, 42, 0.06); box-shadow: var(--shadow); border-radius: 12px; padding: 20px; margin-bottom: 24px; }}
		.viewer-wrapper {{ position: relative; aspect-ratio: 4 / 3; background: #f1f5f9; border-radius: 8px; overflow: hidden; margin-bottom: 16px; }}
		.viewer-wrapper img {{ width: 100%; height: 100%; object-fit: contain; }}
		#grid-mode {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
		.grid-item {{ background: white; border: 1px solid rgba(15, 23, 42, 0.06); border-radius: 8px; overflow: hidden; cursor: pointer; }}
		.grid-img {{ width: 100%; aspect-ratio: 4 / 3; object-fit: contain; background: #f1f5f9; }}
		.grid-label {{ padding: 8px; text-align: center; font-size: 0.875rem; font-weight: 600; }}
		.controls {{ display: grid; gap: 12px; margin-top: 12px; }}
		.controls label {{ font-weight: 600; font-size: 0.875rem; }}
		.controls input[type=range] {{ cursor: pointer; }}
		.info-text {{ font-size: 0.875rem; color: var(--muted); margin-top: 12px; }}

		.attribution {{ margin-top: 48px; padding-top: 24px; border-top: 1px solid rgba(15, 23, 42, 0.06); color: #94a3b8; font-size: 0.875rem; line-height: 1.6; }}
		.attribution a {{ color: #64748b; text-decoration: underline; }}
		@media (max-width: 760px) {{
			.shell {{ width: calc(100vw - 20px); }}
			h1 {{ font-size: 1.75rem; }}
		}}
	</style>
</head>
<body>
	<div class="shell">
		<section class="hero">
			<h1>{escape(project_title)}</h1>
			<p>Interactive tool for comparing historical orthophoto imagery. Select a site and comparison type below.</p>
		</section>
		
		<div class="controls-panel">
			<div class="control-group">
				<label class="control-label">Site</label>
				<select id="site-select" class="control-input" onchange="updateSite()">
					<option>Select a site...</option>
				</select>
			</div>
			
			<div class="control-group">
				<label class="control-label">Comparison Type</label>
				<div class="button-row">
					<button class="button secondary active" onclick="setMode('opacity')" data-mode="opacity">Opacity</button>
					<button class="button secondary" onclick="setMode('grid')" data-mode="grid">Grid</button>
					<button class="button secondary" onclick="setMode('timelapse')" data-mode="timelapse">Timelapse</button>
				</div>
			</div>
			
			<div id="year-selection" class="control-group">
				<label class="control-label">Start Year</label>
				<select id="year-start" class="control-input" onchange="updateComparison()"></select>
				<label class="control-label" style="margin-top: 12px;">End Year</label>
				<select id="year-end" class="control-input" onchange="updateComparison()"></select>
			</div>
			
			<div id="timelapse-controls" style="display: none;" class="control-group">
				<label class="control-label">Year: <span id="tlabel">—</span></label>
				<input id="timelapse-year" type="range" min="0" max="10" value="0" class="control-input" oninput="stepTimelapse(Number(this.value))" style="cursor: pointer;">
				<div class="button-row" style="margin-top: 12px;">
					<button class="button secondary" onclick="stepTimelapse(tlIdx - 1)">&#8592; Prev</button>
					<button class="button" onclick="playTimelapse()" id="btn-play">Play</button>
					<button class="button secondary" onclick="pauseTimelapse()">Pause</button>
					<button class="button secondary" onclick="stepTimelapse(tlIdx + 1)">Next &#8594;</button>
				</div>
				<div style="margin-top: 12px;">
					<label class="control-label">Speed <input id="tl-speed" type="range" min="400" max="3000" value="1500" step="100" class="control-input" style="cursor: pointer;"> <span id="tl-speed-label">1.5 s/frame</span></label>
				</div>
				<p class="info-text">Use Prev/Next for single-year stepping, drag the year slider, or use the keyboard arrow keys while timelapse is active.</p>
			</div>
		</div>
		
		<div class="viewer-panel">
			<div class="viewer-wrapper" id="viewer-wrapper">
				<div id="opacity-mode" style="position: relative; width: 100%; height: 100%;">
					<img id="opacity-base-img" src="" alt="Base" style="width: 100%; height: 100%; object-fit: contain;">
					<img id="opacity-overlay-img" src="" alt="Overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; opacity: 0.5;">
				</div>
				<div id="timelapse-mode" style="display: none; position: relative; width: 100%; height: 100%;">
					<img id="tl-img-a" src="" alt="" style="width: 100%; height: 100%; object-fit: contain; position: absolute; transition: opacity 0.5s ease;">
					<img id="tl-img-b" src="" alt="" style="width: 100%; height: 100%; object-fit: contain; position: absolute; opacity: 0; transition: opacity 0.5s ease;">
				</div>
			</div>
			<div id="grid-mode" style="display: none; margin-top: 12px;"></div>
			
			<div id="opacity-controls" class="controls">
				<label>Overlay opacity <input id="opacity-value" type="range" min="0" max="100" value="50" oninput="applyOpacityBlend()"></label>
			</div>
			
			<div class="info-text" id="viewer-info"></div>
		</div>
		
		<div id="lightbox" onclick="closeLightbox()" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.88); z-index: 1000; cursor: zoom-out;">
			<img id="lightbox-img" src="" alt="" style="max-width: 90vw; max-height: 90vh; position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); border-radius: 4px;">
			<div id="lightbox-label" style="position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%); color: white; font-size: 1.1rem; font-weight: 600; letter-spacing: 0.05em;"></div>
		</div>
		
		<div class="attribution">
			<strong>Data Source & Attribution</strong><br>
			Orthophoto imagery © Cantabria Government via <a href="https://geoservicios.cantabria.es/" target="_blank">GeoServicios Cantabria</a><br>
			Licensed under <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">Creative Commons Attribution 4.0 International (CC-BY-4.0)</a><br>
			<br>
			<strong>Geogander</strong> — Interactive tool for historical imagery comparison
		</div>
	</div>
	
	<script>
		const imageData = {image_data};
		let currentSite = null;
		let currentMode = 'opacity';
		let timelapseTimer = null;
		let tlActive = 'a';
		let tlTransitioning = false;
		let tlQueuedIdx = null;
		
		function init() {{
			const select = document.getElementById('site-select');
			Object.keys(imageData).forEach(site => {{
				const opt = document.createElement('option');
				opt.value = site;
				opt.textContent = site;
				select.appendChild(opt);
			}});
		}}
		
		function updateSite() {{
			currentSite = document.getElementById('site-select').value;
			if (currentSite) {{
				populateYears();
				if (currentMode === 'grid') buildGrid();
				else if (currentMode === 'timelapse') initTimelapse();
				else updateOpacity();
			}}
		}}
		
		function populateYears() {{
			if (!currentSite) return;
			const imgs = imageData[currentSite].images;
			const years = [...new Set(imgs.map(i => i.year))].sort((a, b) => a - b);
			['year-start', 'year-end'].forEach(id => {{
				const sel = document.getElementById(id);
				sel.innerHTML = '';
				years.forEach(y => {{
					const opt = document.createElement('option');
					opt.value = y;
					opt.textContent = y;
					sel.appendChild(opt);
				}});
			}});
			document.getElementById('year-start').value = years[0];
			document.getElementById('year-end').value = years[years.length - 1];
		}}
		
		function setMode(m) {{
			currentMode = m;
			pauseTimelapse();
			document.querySelectorAll('[data-mode]').forEach(b => b.classList.remove('active'));
			document.querySelector(`[data-mode="${{m}}"]`).classList.add('active');
			document.getElementById('viewer-wrapper').style.display = m === 'grid' ? 'none' : '';
			document.getElementById('opacity-mode').style.display = m === 'opacity' ? 'block' : 'none';
			document.getElementById('timelapse-mode').style.display = m === 'timelapse' ? 'block' : 'none';
			document.getElementById('grid-mode').style.display = m === 'grid' ? 'grid' : 'none';
			document.getElementById('opacity-controls').style.display = m === 'opacity' ? 'grid' : 'none';
			document.getElementById('year-selection').style.display = m === 'opacity' ? 'block' : 'none';
			document.getElementById('timelapse-controls').style.display = m === 'timelapse' ? 'block' : 'none';
			if (m === 'grid') buildGrid();
			else if (m === 'timelapse') initTimelapse();
			else updateOpacity();
		}}
		
		function getImg(year) {{
			if (!currentSite) return null;
			return imageData[currentSite].images.find(i => i.year == year);
		}}
		
		function updateComparison() {{
			if (currentMode === 'opacity') updateOpacity();
		}}

		function timelapsePath(img) {{
			return img.timelapse_path || img.path;
		}}
		
		// Opacity mode
		function updateOpacity() {{
			const start = Number(document.getElementById('year-start').value);
			const end = Number(document.getElementById('year-end').value);
			const b = getImg(start), a = getImg(end);
			if (b && a) {{
				document.getElementById('opacity-base-img').src = b.path;
				document.getElementById('opacity-overlay-img').src = a.path;
				applyOpacityBlend();
				document.getElementById('viewer-info').textContent = `Base: ${{start}} | Overlay: ${{end}}`;
			}}
		}}
		
		function applyOpacityBlend() {{
			const v = Number(document.getElementById('opacity-value').value) / 100;
			document.getElementById('opacity-overlay-img').style.opacity = v;
		}}
		
		// Grid mode
		function buildGrid() {{
			if (!currentSite) return;
			const imgs = imageData[currentSite].images;
			const frag = document.createDocumentFragment();
			imgs.forEach(i => {{
				const div = document.createElement('div');
				div.className = 'grid-item';
				div.innerHTML = `<img src="${{i.path}}" class="grid-img" loading="lazy"><div class="grid-label">${{i.year}}</div>`;
				div.addEventListener('click', () => openLightbox(i.path, i.year));
				frag.appendChild(div);
			}});
			const grid = document.getElementById('grid-mode');
			grid.innerHTML = '';
			grid.appendChild(frag);
		}}
		
		function openLightbox(path, year) {{
			document.getElementById('lightbox-img').src = path;
			document.getElementById('lightbox-label').textContent = year;
			document.getElementById('lightbox').style.display = 'block';
		}}
		
		function closeLightbox() {{
			document.getElementById('lightbox').style.display = 'none';
		}}
		
		// Timelapse mode
		let tlIdx = 0;
		
		function initTimelapse() {{
			if (!currentSite) return;
			const imgs = imageData[currentSite].images;
			const slider = document.getElementById('timelapse-year');
			slider.max = imgs.length - 1;
			slider.value = 0;
			tlIdx = 0;
			tlActive = 'a';
			tlTransitioning = false;
			tlQueuedIdx = null;
			const imgA = document.getElementById('tl-img-a');
			const imgB = document.getElementById('tl-img-b');
			imgA.style.transition = 'none';
			imgB.style.transition = 'none';
			imgA.style.opacity = 1;
			imgB.style.opacity = 0;
			imgB.src = '';
			imgA.src = timelapsePath(imgs[0]);
			document.getElementById('tlabel').textContent = imgs[0].year;
			document.getElementById('viewer-info').textContent = imgs[0].year;
			document.getElementById('tl-speed').oninput = function() {{
				document.getElementById('tl-speed-label').textContent = (this.value / 1000).toFixed(1) + ' s/frame';
				if (timelapseTimer) {{ pauseTimelapse(); playTimelapse(); }}
			}};
		}}
		
		function stepTimelapse(idx) {{
			if (!currentSite) return;
			const imgs = imageData[currentSite].images;
			idx = Math.max(0, Math.min(idx, imgs.length - 1));
			if (idx === tlIdx && !tlTransitioning) return;
			if (tlTransitioning) {{
				tlQueuedIdx = idx;
				return;
			}}
			tlTransitioning = true;
			const img = imgs[idx];
			const next = tlActive === 'a' ? 'b' : 'a';
			const nextEl = document.getElementById(`tl-img-${{next}}`);
			const curEl  = document.getElementById(`tl-img-${{tlActive}}`);
			nextEl.style.transition = 'none';
			curEl.style.transition = 'none';
			nextEl.style.opacity = 0;
			const finishStep = () => {{
				tlActive = next;
				tlIdx = idx;
				document.getElementById('timelapse-year').value = idx;
				document.getElementById('tlabel').textContent = img.year;
				document.getElementById('viewer-info').textContent = img.year;
				tlTransitioning = false;
				if (tlQueuedIdx !== null) {{
					const queued = tlQueuedIdx;
					tlQueuedIdx = null;
					if (queued !== tlIdx) stepTimelapse(queued);
				}}
			}};
			const startFade = () => {{
				requestAnimationFrame(() => {{
					nextEl.style.transition = 'opacity 0.4s ease';
					curEl.style.transition  = 'opacity 0.4s ease';
					nextEl.style.opacity = 1;
					curEl.style.opacity  = 0;
					curEl.addEventListener('transitionend', finishStep, {{ once: true }});
				}});
			}};
			nextEl.onload = null;
			nextEl.onerror = null;
			nextEl.src = timelapsePath(img);
			if (nextEl.decode) {{
				nextEl.decode().then(startFade).catch(startFade);
			}} else if (nextEl.complete) {{
				startFade();
			}} else {{
				nextEl.onload = startFade;
				nextEl.onerror = startFade;
			}}
		}}
		
		function playTimelapse() {{
			if (timelapseTimer || !currentSite) return;
			const imgs = imageData[currentSite].images;
			const speed = Number(document.getElementById('tl-speed').value);
			timelapseTimer = setInterval(() => {{
				stepTimelapse((tlIdx + 1) % imgs.length);
			}}, speed);
		}}
		
		function pauseTimelapse() {{
			if (timelapseTimer) {{
				clearInterval(timelapseTimer);
				timelapseTimer = null;
			}}
		}}
		
		document.addEventListener('keydown', e => {{
			if (e.key === 'Escape') closeLightbox();
			if (currentMode === 'timelapse' && currentSite) {{
				if (e.key === 'ArrowRight') stepTimelapse(tlIdx + 1);
				if (e.key === 'ArrowLeft')  stepTimelapse(tlIdx - 1);
			}}
		}});
		
		init();
	</script>
</body>
</html>"""

    return _write_html(output_path, html)
