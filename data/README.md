# Lonta HVAC seasonality source archive

NOAA NCEI monthly U.S. Climate Normals, 1991–2020. Retrieved October 9, 2026. The 24 original station files in `raw/` retain their original bytes; hashes are recorded in `selected.json`. Selection is purposive, with one airport reference for each city label. It does not describe city-wide weather or contractor demand.

Variables: `MLY-HTDD-NORMAL`, `MLY-CLDD-NORMAL` (65°F base), plus their measurement/completeness flags and years fields. CSV values are already decimal °F-days; do not divide them by ten again. Missing −9999 would fail the audit, not become zero.

Sources: [NOAA product](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals), [monthly documentation](https://www.ncei.noaa.gov/pub/data/cdo/documentation/normals-monthly-1991-2020_documentation.pdf), [CSV format](https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/doc/Readme_By-Variable_By-Station_Normals_Files.txt). Each station's original download URL is retained in selected.json and the public export.

From `web/`:

```sh
node scripts/seasonality-test.mjs
python3 scripts/seasonality_audit.py
python3 scripts/seasonality_chart.py
python3 scripts/seasonality-notebook.py
```

The first two checks use existing Node dependencies and Python's standard library. Plotting uses Matplotlib. Notebook generation uses nbformat, nbclient, nbconvert and ipykernel. Validated environment: Python 3.12.8, Matplotlib 3.10.8, nbformat 5.11.1, nbclient 0.11.0, nbconvert 7.17.1, ipykernel 7.4.0. Source checks require no network access or credentials and never silently replace the archive.

`lonta-hvac-seasonality-audit.ipynb` is executed top to bottom with saved outputs; the HTML companion is for readable inspection. Public export calculations live in `lib/research/seasonality.ts`. The plot is generated from the independent Python audit, not from a hand-entered table. The checks validate fidelity to the downloaded NOAA files, not NOAA's underlying climate calculations.
