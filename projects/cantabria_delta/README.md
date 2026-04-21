# Cantabria Delta Project

This project fetches historical orthophotos for the Rio del Escudo delta and prepares data for web-based visual comparison pages.

## Fetch imagery

Run from repository root:

```bash
python scripts/fetch.py --config projects/cantabria_delta/config.yaml
```

Images are saved to `projects/cantabria_delta/data/images/`.

## Output filename convention

Downloaded images now include metadata in the filename:

`<project>__<year>__<service>__layer<id>__<crs>__<bbox-label>__<bbox-coords>__<image-size>.png`

Example:

`cantabria-delta__2024__ortofoto-2024__layer0__epsg-25830__escudo-delta-core__378500-4799000-380500-4800500__1600x1200.png`

## Changing the bbox

Edit [projects/cantabria_delta/config.yaml](projects/cantabria_delta/config.yaml):

- `bbox.label` for a human-readable area tag
- `bbox.coords` for the actual extraction boundary

The fetcher uses exactly the `bbox.coords` value from config for each API request.
