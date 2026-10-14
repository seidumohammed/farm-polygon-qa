"""Row-level and dataset-level checks for farm polygon data.

Each row check takes a GeoDataFrame and returns a boolean Series (True means
the row failed). Checks never drop or edit rows, so a reviewer can see exactly
what is wrong and decide what to do.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box


@dataclass(frozen=True)
class Config:
    expected_epsg: int = 4326
    bbox: tuple[float, float, float, float] | None = None  # minx, miny, maxx, maxy in expected CRS
    min_area_ha: float = 0.1
    max_area_ha: float = 100.0
    area_tolerance: float = 0.20  # allowed relative gap between stated and computed area
    overlap_ratio: float = 0.10  # share of the smaller polygon covered by a neighbour
    min_compactness: float = 0.05  # Polsby-Popper; very low values mean slivers
    id_col: str = "plot_id"
    area_col: str = "area_ha"


@dataclass(frozen=True)
class Check:
    name: str
    severity: str  # "error" must be fixed, "warning" needs a human look
    description: str


CHECKS = {
    "empty_geometry": Check("empty_geometry", "error", "Geometry is missing or empty"),
    "not_polygon": Check("not_polygon", "error", "Geometry is not a polygon (for example a point or line)"),
    "invalid_geometry": Check("invalid_geometry", "error", "Polygon is invalid, such as a self-intersecting bowtie"),
    "missing_id": Check("missing_id", "error", "Plot ID is missing"),
    "duplicate_id": Check("duplicate_id", "error", "Plot ID is used more than once"),
    "duplicate_geometry": Check("duplicate_geometry", "error", "Same shape appears under more than one ID"),
    "outside_bbox": Check("outside_bbox", "error", "Plot lies outside the expected area"),
    "swapped_xy": Check("swapped_xy", "error", "Latitude and longitude look swapped"),
    "too_large": Check("too_large", "error", "Area is above the maximum plausible plot size"),
    "too_small": Check("too_small", "warning", "Area is below the minimum plausible plot size"),
    "sliver": Check("sliver", "warning", "Shape is a thin sliver, often a digitising error"),
    "area_mismatch": Check("area_mismatch", "warning", "Stated area differs from the area computed from the polygon"),
    "overlap": Check("overlap", "warning", "Plot overlaps another plot beyond the allowed share"),
}


def _polygons(gdf: gpd.GeoDataFrame) -> pd.Series:
    return gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])


def empty_geometry(gdf, cfg):
    return gdf.geometry.isna() | gdf.geometry.is_empty


def not_polygon(gdf, cfg):
    return ~empty_geometry(gdf, cfg) & ~_polygons(gdf)


def invalid_geometry(gdf, cfg):
    ok = _polygons(gdf)
    flag = pd.Series(False, index=gdf.index)
    flag.loc[ok] = (~gdf.geometry[ok].is_valid).to_numpy()
    return flag


def missing_id(gdf, cfg):
    col = gdf[cfg.id_col]
    return col.isna() | (col.astype(str).str.strip() == "")


def duplicate_id(gdf, cfg):
    col = gdf[cfg.id_col]
    return col.notna() & col.duplicated(keep=False)


def duplicate_geometry(gdf, cfg):
    ok = _polygons(gdf) & ~empty_geometry(gdf, cfg)
    flag = pd.Series(False, index=gdf.index)
    wkb = gdf.geometry[ok].normalize().to_wkb()
    flag.loc[ok] = (wkb.duplicated(keep=False)).to_numpy()
    return flag


def outside_bbox(gdf, cfg):
    if cfg.bbox is None:
        return pd.Series(False, index=gdf.index)
    ok = ~empty_geometry(gdf, cfg)
    flag = pd.Series(False, index=gdf.index)
    flag.loc[ok] = (~gdf.geometry[ok].within(box(*cfg.bbox))).to_numpy()
    return flag


def swapped_xy(gdf, cfg):
    if cfg.bbox is None:
        return pd.Series(False, index=gdf.index)
    minx, miny, maxx, maxy = cfg.bbox
    ok = ~empty_geometry(gdf, cfg)
    flag = pd.Series(False, index=gdf.index)
    c = gdf.geometry[ok].representative_point()
    inside = (c.x.between(minx, maxx)) & (c.y.between(miny, maxy))
    swapped_inside = (c.y.between(minx, maxx)) & (c.x.between(miny, maxy))
    flag.loc[ok] = ((~inside) & swapped_inside).to_numpy()
    return flag


def _area_ha(gdf, cfg) -> pd.Series:
    ok = _polygons(gdf) & ~empty_geometry(gdf, cfg) & ~invalid_geometry(gdf, cfg)
    area = pd.Series(np.nan, index=gdf.index)
    if ok.any():
        sub = gdf[ok]
        area[ok] = sub.to_crs(sub.estimate_utm_crs()).geometry.area / 10_000
    return area


def too_large(gdf, cfg):
    return _area_ha(gdf, cfg) > cfg.max_area_ha


def too_small(gdf, cfg):
    return _area_ha(gdf, cfg) < cfg.min_area_ha


def sliver(gdf, cfg):
    ok = _polygons(gdf) & ~empty_geometry(gdf, cfg) & ~invalid_geometry(gdf, cfg)
    flag = pd.Series(False, index=gdf.index)
    if ok.any():
        sub = gdf[ok]
        proj = sub.to_crs(sub.estimate_utm_crs()).geometry
        compactness = 4 * np.pi * proj.area / (proj.length**2)
        flag.loc[ok] = (compactness < cfg.min_compactness).to_numpy()
    return flag


def area_mismatch(gdf, cfg):
    if cfg.area_col not in gdf.columns:
        return pd.Series(False, index=gdf.index)
    stated = pd.to_numeric(gdf[cfg.area_col], errors="coerce")
    computed = _area_ha(gdf, cfg)
    gap = (stated - computed).abs() / computed.replace(0, np.nan)
    return stated.notna() & computed.notna() & (gap > cfg.area_tolerance)


def overlap(gdf, cfg):
    ok = _polygons(gdf) & ~empty_geometry(gdf, cfg) & ~invalid_geometry(gdf, cfg)
    flag = pd.Series(False, index=gdf.index)
    if ok.sum() < 2:
        return flag
    sub = gdf[ok]
    proj = sub.to_crs(sub.estimate_utm_crs()).geometry.reset_index(drop=True)
    index = sub.index.to_list()
    tree = proj.sindex
    left, right = tree.query(proj, predicate="intersects")
    for i, j in zip(left, right):
        if i >= j:
            continue
        inter = proj.iloc[i].intersection(proj.iloc[j]).area
        smaller = min(proj.iloc[i].area, proj.iloc[j].area)
        if smaller > 0 and inter / smaller > cfg.overlap_ratio:
            flag[index[i]] = True
            flag[index[j]] = True
    return flag


ROW_CHECKS = {
    "empty_geometry": empty_geometry,
    "not_polygon": not_polygon,
    "invalid_geometry": invalid_geometry,
    "missing_id": missing_id,
    "duplicate_id": duplicate_id,
    "duplicate_geometry": duplicate_geometry,
    "outside_bbox": outside_bbox,
    "swapped_xy": swapped_xy,
    "too_large": too_large,
    "too_small": too_small,
    "sliver": sliver,
    "area_mismatch": area_mismatch,
    "overlap": overlap,
}
