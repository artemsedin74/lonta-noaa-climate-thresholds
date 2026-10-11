# Lonta HVAC seasonality source archive

NOAA NCEI monthly U.S. Climate Normals, 1991–2020. Retrieved October 9, 2026. The 24 original station files in `raw/` retain their original bytes; hashes are recorded in `selected.json`. Selection is purposive, with one airport reference for each city label. It does not describe city-wide weather or contractor demand.

Variables: `MLY-HTDD-NORMAL`, `MLY-CLDD-NORMAL` (65°F base), plus their measurement/completeness flags and years fields. CSV values are already decimal °F-days; do not divide them by ten again. Missing −9999 would fail the audit, not become zero.

Sources: [NOAA product](https://www.ncei.noaa.gov/products/land-based-station/us-climate-normals), [monthly documentation](https://www.ncei.noaa.gov/pub/data/cdo/documentation/normals-monthly-1991-2020_documentation.pdf), [CSV format](https://www.ncei.noaa.gov/data/normals-monthly/1991-2020/doc/Readme_By-Variable_By-Station_Normals_Files.txt). Each station's original download URL is retained in selected.json and the public export.

The original site's audit notebooks and HTML output are preserved here for
inspection. Their build scripts ran in the Lonta website workspace, which is
not included in this repository. To reproduce this repository's comparison,
run the following from its root:

```sh
python3 analysis.py --no-chart
python3 -m unittest discover -s tests -v
```

The comparison and its tests use Python's standard library. Plotting uses
Matplotlib and numpy. Source checks require no network access or credentials
and never silently replace the archive. See the root `VALIDATION.json` for the
recorded comparison run, and the root README for optional figure regeneration.

`lonta-hvac-seasonality-audit.ipynb` has saved outputs from the site's audit;
the HTML companion is for readable inspection. These checks validate fidelity
to the downloaded NOAA files, not NOAA's underlying climate calculations.
