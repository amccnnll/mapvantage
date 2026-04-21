# Site Bounding Boxes (EPSG:25830)

This file stores reusable site extents for manual copy/paste into project config.

## Oyambre (BBOX1)

Input corners:

- SE: 394216.075, 4802445.188
- NW: 391468.764, 4804825.562

Normalized ArcGIS bbox (xmin,ymin,xmax,ymax):

391468.764,4802445.188,394216.075,4804825.562

Ready-to-paste config block:

```yaml
bbox:
  label: "oyambre"
  coords: "391468.764,4802445.188,394216.075,4804825.562"
```

## Santander (BBOX2)

Input corners:

- SE: 441318.857, 4808959.947
- NW: 438207.351, 4811288.285

Extended south by 100 m:

- New south edge: 4808859.947

Normalized ArcGIS bbox (xmin,ymin,xmax,ymax):

438207.351,4808859.947,441318.857,4811288.285

Ready-to-paste config block:

```yaml
bbox:
  label: "santander"
  coords: "438207.351,4808859.947,441318.857,4811288.285"
```
