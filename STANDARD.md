# Farm polygon data standard (proposed template)

This is a working template for how a team can collect, check, and release
farm polygon data. It is written to be adapted. The thresholds are defaults,
and they should be set with the people who collect the data.

## 1. Purpose and scope

Farm plot polygons feed deforestation screening, traceability reports, and
programme decisions. Bad polygons produce wrong results that look right on a
map. This standard sets the minimum a polygon file must meet before anyone
uses it for analysis or reporting.

It covers polygon files (GeoJSON, GeoPackage, Shapefile) of farm plots. It
does not cover satellite imagery or non-farm layers.

## 2. Required fields

| Field | Rule |
|---|---|
| `plot_id` | Present, unique, never reused. One ID per physical plot. |
| `area_ha` | Optional. If given, it should match the polygon within 20%. |
| Geometry | A valid Polygon or MultiPolygon. |

Extra fields (farmer ID, community, collector, date) are allowed. Keep their
names stable between deliveries.

## 3. Coordinate system

- Store and exchange data in **EPSG:4326** (WGS 84, longitude and latitude).
- A file with no coordinate system is rejected until someone confirms it.
- Area and overlap are always computed in a local projected system (UTM), never
  in degrees.

## 4. Geometry rules

A polygon must:

- be valid (no self-crossing outlines or unclosed rings),
- not be empty, and not be a point or line,
- sit inside the expected area for the project,
- have latitude and longitude the right way round,
- have an area between **0.1 ha and 100 ha** (default limits),
- not be a thin sliver (compactness below 0.05 is flagged),
- not overlap another plot by more than **10%** of the smaller plot,
- not be an exact copy of another plot under a different ID.

## 5. What each result means

| Severity | Meaning | Action |
|---|---|---|
| Error | The record cannot be trusted as it is. | Fix it or return it to the collector. Do not use it in analysis. |
| Warning | The record may be correct but is unusual. | A reviewer looks at it, confirms or corrects it, and notes the decision. |
| OK | No check failed. | Can be used. |

Rows are flagged, never deleted. The original record always stays in the file.

## 6. Roles and workflow

1. **Collector (field officer)** captures the polygon and submits it.
2. **Analyst** runs the QA tool on each delivery and sends the issue list back.
3. **Team lead** reviews warnings and decides whether to keep, correct, or
   re-collect each plot.
4. **Data lead** signs off the cleaned file for release and records the version.

Each delivery is checked on arrival, before it is merged into the main dataset.

## 7. Versioning and records

- Name files `<project>_plots_<YYYY-MM-DD>_v<number>`.
- Keep the QA report (`report.md` and `issues.csv`) with every released file.
- Record who reviewed each warning and what was decided.
- Never overwrite a released file. Issue a new version.

## 8. Review of this standard

Review the thresholds after the first three deliveries, using the warnings
that reviewers marked as correct. If most plots flagged "too small" are real,
lower the minimum. If one collector causes most errors, retrain that collector
before changing the rules.
