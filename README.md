# Farm Polygon QA

A command-line tool and a written data standard for checking farm plot
polygons before they are used for analysis or reporting.

Farm polygons are collected in the field by many people and are often messy.
This tool flags the problems, never deletes records, and writes a report that
a reviewer can work through. [STANDARD.md](STANDARD.md) sets out the rules,
roles, and workflow around it.

All data in this repository is **synthetic**. The plots are fabricated around
Sefwi-Wiawso, Ghana, with faults planted at known positions so that every
check can be tested. The tool has not been run on real farmer data, and the
default thresholds have not been validated against real field data.

## Run it

```bash
pip install -r requirements.txt
python -m polyqa.synthetic                      # writes data/synthetic_plots.geojson
python -m polyqa data/synthetic_plots.geojson --out reports --bbox -2.80 6.00 -2.30 6.40
pytest
```

Options: `--bbox` (expected area in longitude/latitude), `--min-area-ha`,
`--max-area-ha`, `--id-col`, `--area-col`. The command exits with code 1 when
any error-level issue is found, so it can gate a pipeline.

## Checks

| Check | Severity | Catches |
|---|---|---|
| empty_geometry | error | Missing or empty geometry |
| not_polygon | error | Points or lines in a polygon file |
| invalid_geometry | error | Self-crossing outlines |
| missing_id | error | Blank plot ID |
| duplicate_id | error | One ID used more than once |
| duplicate_geometry | error | Same shape under different IDs |
| outside_bbox | error | Plot outside the expected area |
| swapped_xy | error | Latitude and longitude the wrong way round |
| too_large | error | Area above the maximum |
| too_small | warning | Area below the minimum |
| sliver | warning | Thin shapes from digitising errors |
| area_mismatch | warning | Stated area differs from computed area by more than 20% |
| overlap | warning | Overlap above 10% of the smaller plot |

Dataset-level checks report a missing coordinate system, or a system other
than EPSG:4326 (the data is reprojected for checking).

## Result on the synthetic file

74 plots: 58 clean, 5 warnings, 11 errors. The 58 clean plots raise no flags,
and each flag traces to a planted fault. See [reports/report.md](reports/report.md)
and `reports/issues.csv`. Fourteen faults were planted; the extra flags come
from planted pairs (the duplicate shape also overlaps its original, and the
swapped plot is also outside the area).

## Limits

- Thresholds are defaults, not evidence-based values. Set them with the people
  who collect the data (see section 8 of the standard).
- Areas and overlaps use an automatically chosen UTM zone, which is accurate
  for plots in one zone and less so for data spread across zones.
- The tool flags problems. It does not repair geometry.
- It checks geometry and basic attributes. It does not compare polygons to
  satellite imagery.

## Related

The plot checks in [eudr-plot-risk-checker](https://github.com/seidumohammed/eudr-plot-risk-checker)
cover invalid geometry, duplicate IDs, out-of-area, and implausible area. This
project adds overlaps, duplicate shapes, swapped coordinates, slivers, area
mismatches, coordinate system checks, a report, and the written standard.
