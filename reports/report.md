# QA report: synthetic_plots.geojson

Plots checked: **74**

- Clean: 58
- Need review (warning): 5
- Must fix (error): 11

## Issues by check

| Check | Severity | Plots | What it means |
|---|---|---|---|
| area_mismatch | warning | 1 | Stated area differs from the area computed from the polygon |
| duplicate_geometry | error | 2 | Same shape appears under more than one ID |
| duplicate_id | error | 2 | Plot ID is used more than once |
| empty_geometry | error | 1 | Geometry is missing or empty |
| invalid_geometry | error | 1 | Polygon is invalid, such as a self-intersecting bowtie |
| missing_id | error | 1 | Plot ID is missing |
| not_polygon | error | 1 | Geometry is not a polygon (for example a point or line) |
| outside_bbox | error | 2 | Plot lies outside the expected area |
| overlap | warning | 4 | Plot overlaps another plot beyond the allowed share |
| sliver | warning | 1 | Shape is a thin sliver, often a digitising error |
| swapped_xy | error | 1 | Latitude and longitude look swapped |
| too_large | error | 1 | Area is above the maximum plausible plot size |
| too_small | warning | 2 | Area is below the minimum plausible plot size |

Rows are flagged, never deleted. Fix or confirm each flagged plot, then re-run.
