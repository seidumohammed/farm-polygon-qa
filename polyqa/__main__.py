"""Command line: python -m polyqa plots.geojson --out reports --bbox -3.2 5.9 -2.0 6.8"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd

from polyqa.checks import Config
from polyqa.qa import run_qa, write_report


def main() -> int:
    p = argparse.ArgumentParser(description="Quality checks for farm polygon data")
    p.add_argument("input", type=Path, help="GeoJSON, GeoPackage or Shapefile")
    p.add_argument("--out", type=Path, default=Path("reports"))
    p.add_argument("--bbox", type=float, nargs=4, metavar=("MINX", "MINY", "MAXX", "MAXY"),
                   help="Expected extent in EPSG:4326; enables out-of-area and swapped-coordinate checks")
    p.add_argument("--min-area-ha", type=float, default=Config.min_area_ha)
    p.add_argument("--max-area-ha", type=float, default=Config.max_area_ha)
    p.add_argument("--id-col", default=Config.id_col)
    p.add_argument("--area-col", default=Config.area_col)
    args = p.parse_args()

    cfg = Config(bbox=tuple(args.bbox) if args.bbox else None, min_area_ha=args.min_area_ha,
                 max_area_ha=args.max_area_ha, id_col=args.id_col, area_col=args.area_col)
    gdf = gpd.read_file(args.input)
    work, issues, dataset_issues = run_qa(gdf, cfg)
    paths = write_report(work, issues, dataset_issues, args.out, args.input.name)

    counts = work["qa_status"].value_counts().to_dict()
    print(f"{len(work)} plots: {counts.get('ok', 0)} ok, {counts.get('warning', 0)} warning, "
          f"{counts.get('error', 0)} error. Report: {paths['report']}")
    return 1 if counts.get("error", 0) or any(d["severity"] == "error" for d in dataset_issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
