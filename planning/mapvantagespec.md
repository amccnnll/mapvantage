# Analysis of Historical Imagery

This document outlines the technical framework for accessing, extracting, and analyzing historical geographic data from the **Mapas Cantabria** portal (SITCAN), with a focus on the marshlands and mudflats of the Río del Escudo.

---

## 1. Licensing & Legal Framework

The geographic data provided by the Government of Cantabria is governed by an Open Data policy designed for reuse.

- **Legal Basis:** Spanish Law 37/2007 on the reuse of public sector information.
- **License Type:** Equivalent to **CC BY 4.0** (Creative Commons Attribution).
- **Permitted Use:** Commercial and non-commercial use, redistribution, and adaptation are allowed.
- **Attribution Requirement:** You must credit the source as:
  > _"Gobierno de Cantabria. Sistema de Información Territorial de Cantabria (SITCAN)"_

---

## 2. API Access & Data Extraction

The infrastructure is powered by ArcGIS Server, supporting OGC standards (WMS, WMTS, WCS) and the ArcGIS REST API.

### Service Endpoints

- **Main Directory:** [https://geoservicios.cantabria.es/inspire/rest/services/](https://geoservicios.cantabria.es/inspire/rest/services/)
- **Historical Archive:** Look for the `Historico_Ortofoto` folder.
- **WMS (Web Map Service):** `https://geoservicios.cantabria.es/inspire/services/Ortofoto_Series_WMS/MapServer/WMSServer`

### Extraction Methods

1.  **Tiles (WMTS):** Ideal for high-performance background maps.
2.  **ExportMap (REST):** Best for programmatic extraction of specific bounding boxes.
3.  **WCS (Web Coverage Service):** Essential if you require raw pixel data (GeoTIFF) rather than rendered images (PNG/JPG) for spectral analysis.

---

## 3. QGIS Workflow: Feature Tracking & Measurement

To analyze the evolution of the Río del Escudo mudflats, follow this rigorous spatial workflow:

1.  **Environment Setup:**
    - Set the Project CRS to **EPSG:25830** (ETRS89 / UTM zone 30N). This minimizes distortion for distance calculations in Cantabria.
2.  **Layer Integration:**
    - `Layer` > `Add Layer` > `WMS/WMTS Layer`.
    - Connect to the SITCAN WMS and add the **1956 (Vuelo Americano)** and **2024 (Modern)** layers.
3.  **Digitization:**
    - Create a new **GeoPackage Point Layer** (EPSG:25830).
    - Place a marker on a feature (e.g., a specific tidal creek junction) in the 1956 layer.
    - Place a second marker on the same feature's position in the 2024 layer.
4.  **Analysis:**
    - Use the **Points to Path** tool (Processing Toolbox) to create a vector line between markers.
    - Use the **Field Calculator** on the line layer with the expression `$length` to calculate displacement in meters.
    - _Alternative:_ Use a **Polygon Layer** to trace marsh areas and the **Symmetrical Difference** tool to identify land gain (sedimentation) vs. loss (erosion).

---

## 4. Python Workflow: Automated Extraction

The following script automates the extraction of historical vs. modern imagery for the Río del Escudo estuary.

```python
import requests
import geopandas as gpd
from shapely.geometry import Point

# 1. Spatial Configuration (EPSG:25830)
# Bounding Box for the Río del Escudo mouth/marshes
escudo_bbox = "378500,4799000,380500,4800500"

# 2. API Endpoints
# Layer 0 in Historico_Ortofoto is typically the 1956 Vuelo Americano B
HISTORICAL_URL = "[https://geoservicios.cantabria.es/inspire/rest/services/Historico_Ortofoto/MapServer/export](https://geoservicios.cantabria.es/inspire/rest/services/Historico_Ortofoto/MapServer/export)"
MODERN_URL = "[https://geoservicios.cantabria.es/inspire/rest/services/Ortofoto_2024/MapServer/export](https://geoservicios.cantabria.es/inspire/rest/services/Ortofoto_2024/MapServer/export)"

def save_image(year, url, bbox):
    params = {
        'bbox': bbox,
        'bboxSR': '25830',
        'layers': 'show:0',
        'size': '1600,1200',
        'format': 'png',
        'f': 'image'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        filename = f"escudo_{year}.png"
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Successfully saved {filename}")
    except Exception as e:
        print(f"Error downloading {year}: {e}")

# 3. Execution
save_image("1956", HISTORICAL_URL, escudo_bbox)
save_image("2024", MODERN_URL, escudo_bbox)

# 4. Example Geometric Analysis (Displacement)
# Coordinates for a shifting sand bar or marsh edge
p_early = Point(379500, 4799800)
p_late = Point(379545, 4799820)

gdf = gpd.GeoSeries([p_early, p_late], crs="EPSG:25830")
distance = p_early.distance(p_late)
print(f"Calculated displacement: {distance:.2f} meters.")
```
