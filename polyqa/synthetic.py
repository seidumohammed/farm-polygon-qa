"""Synthetic farm plots near Sefwi-Wiawso, Ghana, with known faults planted.

All data is fabricated. It exists so every check can be tested against a fault
whose location is known, and so the tool can be demonstrated without real
farmer data.
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, Point, Polygon

ORIGIN = (-2.60, 6.15)  # lon, lat
M_PER_DEG_LAT = 110_600.0
M_PER_DEG_LON = 110_300.0  # at about 6 degrees north
BBOX = (-2.80, 6.00, -2.30, 6.40)


def _square(cx_m: float, cy_m: float, side_m: float, rng: np.random.Generator) -> Polygon:
    half = side_m / 2
    jitter = rng.uniform(-0.08, 0.08, size=(4, 2)) * side_m
    pts = [(-half, -half), (half, -half), (half, half), (-half, half)]
    ring = [
        (ORIGIN[0] + (cx_m + x + jx) / M_PER_DEG_LON, ORIGIN[1] + (cy_m + y + jy) / M_PER_DEG_LAT)
        for (x, y), (jx, jy) in zip(pts, jitter)
    ]
    return Polygon(ring)


def make_plots(seed: int = 7, n_clean: int = 60) -> tuple[gpd.GeoDataFrame, dict[str, str]]:
    """Returns (plots, faults) where faults maps plot_id -> expected check name."""
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for i in range(n_clean):
        col, row = i % 10, i // 10
        side = rng.uniform(120, 190)  # about 1.4 to 3.6 ha
        poly = _square(col * 400, row * 400, side, rng)
        rows.append({"plot_id": f"P{i:03d}", "geometry": poly})

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf["area_ha"] = (gdf.to_crs(gdf.estimate_utm_crs()).geometry.area / 10_000).round(2)

    faults: dict[str, str] = {}
    extra: list[dict] = []

    def add(pid, geom, check, area=None):
        extra.append({"plot_id": pid, "geometry": geom, "area_ha": area})
        if check:
            faults[pid] = check

    base = ORIGIN
    far_row = 8  # keep planted faults away from the clean grid
    y0 = far_row * 400

    bow = Polygon([
        (base[0] + 0 / M_PER_DEG_LON, base[1] + y0 / M_PER_DEG_LAT),
        (base[0] + 150 / M_PER_DEG_LON, base[1] + (y0 + 150) / M_PER_DEG_LAT),
        (base[0] + 150 / M_PER_DEG_LON, base[1] + y0 / M_PER_DEG_LAT),
        (base[0] + 0 / M_PER_DEG_LON, base[1] + (y0 + 150) / M_PER_DEG_LAT),
    ])
    add("F_invalid", bow, "invalid_geometry", 2.0)
    add("F_empty", Polygon(), "empty_geometry", 2.0)
    add("F_point", Point(base[0] + 600 / M_PER_DEG_LON, base[1] + y0 / M_PER_DEG_LAT), "not_polygon", 2.0)
    add(None, _square(900, y0, 150, rng), "missing_id", 2.2)
    add("P001", _square(1300, y0, 150, rng), "duplicate_id", 2.2)  # reuses an existing ID
    dup_src = gdf.loc[gdf.plot_id == "P005", "geometry"].iloc[0]
    add("F_dupgeom", dup_src, "duplicate_geometry", float(gdf.loc[gdf.plot_id == "P005", "area_ha"].iloc[0]))
    add("F_outside", _square(900000, 900000, 150, rng), "outside_bbox", 2.2)
    swapped = Polygon([(y, x) for x, y in _square(2000, y0, 150, rng).exterior.coords])
    add("F_swapped", swapped, "swapped_xy", 2.2)
    add("F_large", _square(3000, y0, 1100, rng), "too_large", 120.0)
    add("F_small", _square(3600, y0, 25, rng), "too_small", 0.06)
    sliver = Polygon([
        (base[0] + 4000 / M_PER_DEG_LON, base[1] + y0 / M_PER_DEG_LAT),
        (base[0] + 4300 / M_PER_DEG_LON, base[1] + y0 / M_PER_DEG_LAT),
        (base[0] + 4300 / M_PER_DEG_LON, base[1] + (y0 + 3) / M_PER_DEG_LAT),
        (base[0] + 4000 / M_PER_DEG_LON, base[1] + (y0 + 3) / M_PER_DEG_LAT),
    ])
    add("F_sliver", sliver, "sliver", 0.09)
    mismatch = _square(4800, y0, 150, rng)
    add("F_areamismatch", mismatch, "area_mismatch", 9.0)  # stated 9 ha, real about 2.2
    ov_a = _square(5500, y0, 150, rng)
    ov_b = _square(5550, y0, 150, rng)  # shifted 50 m: heavy overlap with ov_a
    add("F_overlap_a", ov_a, "overlap", 2.2)
    add("F_overlap_b", ov_b, "overlap", 2.2)

    out = gpd.GeoDataFrame(list(gdf.to_dict("records")) + extra, crs="EPSG:4326")
    return out, faults


if __name__ == "__main__":
    from pathlib import Path

    plots, faults = make_plots()
    out = Path("data")
    out.mkdir(exist_ok=True)
    plots.to_file(out / "synthetic_plots.geojson", driver="GeoJSON")
    print(f"Wrote {len(plots)} plots with {len(faults)} planted faults to {out / 'synthetic_plots.geojson'}")
