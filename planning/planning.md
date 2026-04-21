# Geogander Project Plan - Phase 1: MVP

## Overview

Geogander is a tool for creating interactive web-based visual comparisons of historical imagery. Start with the absolute basics:

1. **Fetch imagery** from mapping APIs (SITCAN, etc.)
2. **Create web visualization tools** for easy visual comparison (sliders, opacity blends, grids, timelapses)

That's it. Everything else is a wishlist.

## Progress Tracker

- [x] Phase 1 complete: legacy archive and minimal project structure
- [x] Phase 2 complete: working API fetcher in `src/geogander/fetcher.py`
- [x] Phase 4.1 complete: `scripts/fetch.py` reads project YAML and downloads imagery
- [x] Fetch validation complete: real run saved `1956.png`, `1980.png`, `2000.png`, `2024.png`
- [x] Fetch output naming improved: filenames now include project/service/layer/CRS/bbox/size metadata
- [x] Phase 3 complete: HTML comparison generators implemented in `src/geogander/html_gen.py`
- [x] Phase 4.2 complete: `scripts/visualize.py` generates static comparison pages and indexes
- [x] Phase 5 complete: working comparison pages generated in `projects/cantabria_delta/web/`

---

## Phase 1: Repository Restructuring & Legacy Management

### 1.1 Archive Existing Saltmarsh Project

Move all legacy code to `legacy/saltmarsh/`:

- `src/` (creek_extraction.py, creek_refinement.py, etc.)
- `data/` (Kincardine & Skinflats imagery)
- `creek_tests_*/` (test outputs)
- `docs/` (old HTML visualizations)
- `*.json` files

### 1.2 Minimal Project Structure

```
geogander/
├── src/
│   └── geogander/
│       ├── __init__.py
│       ├── fetcher.py              (fetch imagery from API)
│       ├── html_gen.py             (generate HTML comparison tools)
│       └── config.py               (settings)
├── projects/
│   └── cantabria_delta/
│       ├── README.md
│       ├── config.yaml             (bbox, CRS, years to fetch)
│       ├── data/
│       │   └── images/             (downloaded imagery)
│       └── web/                    (generated HTML files)
├── scripts/
│   ├── fetch.py                    (download imagery)
│   └── visualize.py                (generate HTML comparisons)
├── requirements.txt
├── README.md
└── legacy/
    └── saltmarsh/                  (archived old project)
```

---

## Phase 2: Fetcher Module

Simple tool to download imagery from APIs.

**File:** `src/geogander/fetcher.py`

**Key Function:**

```python
def fetch_imagery(api_url, bbox, year, output_path):
    """Download image for given bbox and year"""
    # Make HTTP request to API
    # Save image to output_path
```

**That's it.** No caching sophistication, no preprocessing.

---

## Phase 3: Web Visualization Generator

Create interactive HTML comparison tools.

**File:** `src/geogander/html_gen.py`

**Key Functions:**

1. **Slider Comparison** — Before/after slider (swipe between two images)
2. **Opacity Blend** — Overlay two images with adjustable transparency
3. **Grid View** — Multiple years displayed in a grid
4. **Timelapse** — Animated sequence through years

Each generates a standalone HTML file (self-contained, no dependencies).

---

## Phase 4: CLI Scripts

### 4.1 `scripts/fetch.py`

Download imagery for a project.

```bash
python scripts/fetch.py --config projects/cantabria_delta/config.yaml
```

Reads config, calls `fetcher.fetch_imagery()` for each year, saves to `projects/*/data/images/`.

### 4.2 `scripts/visualize.py`

Generate HTML comparison tools.

```bash
python scripts/visualize.py --project cantabria_delta --type slider,opacity,grid,timelapse
```

Reads images from `data/images/`, calls `html_gen.*()` functions, outputs to `projects/*/web/`.

---

## Phase 5: Cantabria Delta Example Project

### 5.1 Structure

```
projects/cantabria_delta/
├── README.md                       (what this project is)
├── config.yaml                     (SITCAN endpoint, bbox, CRS, years)
├── data/
│   └── images/                     (1956.png, 1980.png, 2000.png, 2024.png, etc.)
└── web/                            (generated HTML files)
    ├── index.html                  (landing page)
    ├── slider_1956_2024.html       (slider comparison)
    ├── opacity_blend.html          (opacity blend)
    ├── grid_view.html              (grid of all years)
    ├── timelapse.html              (animated sequence)
    └── data/                       (image tiles, any supporting data)
```

### 5.2 config.yaml Example

```yaml
api:
  base_url: "https://geoservicios.cantabria.es/inspire/rest/services"
  service: "Historico_Ortofoto"
  endpoint: "/MapServer/export"

bbox:
  coords: "378500,4799000,380500,4800500" # UTM 30N

crs: "EPSG:25830"
years: [1956, 1980, 2000, 2024]
image_size: "1600x1200"
```

---

## Dependencies

```
requests>=2.28.0
pillow>=9.0.0
pyyaml>=6.0.0
jinja2>=3.1.0
```

Optional:

- `pyproj` if CRS transformations needed
- `opencv-python` for image adjustments (optional)

---

## Deliverables

- [x] Legacy saltmarsh archived to `legacy/`
- [x] `fetcher.py` — Downloads imagery from API
- [x] `projects/cantabria_delta/config.yaml` — Valid YAML and SITCAN service mapping
- [x] Fetched sample set for Cantabria delta (`1956`, `1980`, `2000`, `2024`)
- [x] `html_gen.py` — Generates 4 types of HTML comparison tools
- [x] `scripts/visualize.py` — Generates HTML from downloaded imagery
- [x] Cantabria delta example project with working visualizations
- [x] All HTML deployable directly to GitHub Pages

---

## Timeline

| Task                  | Duration |
| --------------------- | -------- |
| Archive legacy        | 1 day    |
| Build fetcher         | 1 day    |
| Build HTML generators | 2 days   |
| CLI scripts           | 1 day    |
| Cantabria example     | 1 day    |
| GitHub Pages setup    | 1 day    |

**Total: ~7 days**

---

## What's NOT in MVP (Future Wishlist)

- Image processing/enhancement (align, contrast boost, color normalize)
- Change detection/analysis
- Spatial displacement tracking
- Caching layer
- Package installer
- Comprehensive documentation
- Tests
- Docker
- API server
- ML-based feature detection
- Publishing to PyPI

The above are all great future additions, but MVP is just: **fetch → visualize**.
