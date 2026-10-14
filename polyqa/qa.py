"""Run all checks, build the issues table and write the QA report."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import geopandas as gpd
import pandas as pd

from polyqa.checks import CHECKS, ROW_CHECKS, Config


def check_crs(gdf: gpd.GeoDataFrame, cfg: Config) -> list[dict]:
    """Dataset-level CRS problems. Returns a list of issue dicts."""
    if gdf.crs is None:
        return [{"check": "crs_missing", "severity": "error",
                 "detail": "Dataset has no coordinate reference system defined"}]
    if gdf.crs.to_epsg() != cfg.expected_epsg:
        return [{"check": "crs_unexpected", "severity": "warning",
                 "detail": f"CRS is {gdf.crs.to_string()}, expected EPSG:{cfg.expected_epsg}; data was reprojected for checking"}]
    return []


def run_qa(gdf: gpd.GeoDataFrame, cfg: Config | None = None) -> tuple[gpd.GeoDataFrame, pd.DataFrame, list[dict]]:
    """Returns (flagged plots, issues table, dataset-level issues).

    Rows are never dropped. Each check adds a `flag_<name>` column, and
    `qa_status` is "error", "warning" or "ok" for the worst problem on a row.
    """
    cfg = cfg or Config()
    dataset_issues = check_crs(gdf, cfg)

    work = gdf.copy()
    if work.crs is None:
        work = work.set_crs(epsg=cfg.expected_epsg)  # assumed so the other checks can run; reported above
    elif work.crs.to_epsg() != cfg.expected_epsg:
        work = work.to_crs(epsg=cfg.expected_epsg)
    if cfg.id_col not in work.columns:
        work[cfg.id_col] = pd.NA
        dataset_issues.append({"check": "id_column_missing", "severity": "error",
                               "detail": f"Column '{cfg.id_col}' is not in the dataset"})

    for name, fn in ROW_CHECKS.items():
        work[f"flag_{name}"] = fn(work, cfg).fillna(False).astype(bool)

    rows = []
    for name, check in CHECKS.items():
        for idx in work.index[work[f"flag_{name}"]]:
            rows.append({"row": idx, "plot_id": work.at[idx, cfg.id_col], "check": name,
                         "severity": check.severity, "detail": check.description})
    issues = pd.DataFrame(rows, columns=["row", "plot_id", "check", "severity", "detail"])

    status = pd.Series("ok", index=work.index)
    status[issues.loc[issues.severity == "warning", "row"].unique()] = "warning"
    status[issues.loc[issues.severity == "error", "row"].unique()] = "error"
    work["qa_status"] = status
    return work, issues, dataset_issues


def write_report(work: gpd.GeoDataFrame, issues: pd.DataFrame, dataset_issues: list[dict],
                 out_dir: Path, source: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    issues_csv = out_dir / "issues.csv"
    issues.to_csv(issues_csv, index=False)

    counts = work["qa_status"].value_counts().to_dict()
    total = len(work)
    by_check = issues.groupby(["check", "severity"]).size().reset_index(name="plots") if len(issues) else issues

    lines = [f"# QA report: {source}", "", f"Plots checked: **{total}**", "",
             f"- Clean: {counts.get('ok', 0)}",
             f"- Need review (warning): {counts.get('warning', 0)}",
             f"- Must fix (error): {counts.get('error', 0)}", ""]
    if dataset_issues:
        lines += ["## Dataset-level issues", ""]
        lines += [f"- **{d['severity']}** {d['check']}: {d['detail']}" for d in dataset_issues] + [""]
    lines += ["## Issues by check", ""]
    if len(by_check):
        lines += ["| Check | Severity | Plots | What it means |", "|---|---|---|---|"]
        for r in by_check.itertuples():
            lines.append(f"| {r.check} | {r.severity} | {r.plots} | {CHECKS[r.check].description} |")
    else:
        lines.append("No issues found.")
    lines += ["", "Rows are flagged, never deleted. Fix or confirm each flagged plot, then re-run.", ""]
    report_md = out_dir / "report.md"
    report_md.write_text("\n".join(lines), encoding="utf-8")

    flagged = out_dir / "plots_flagged.geojson"
    work.to_file(flagged, driver="GeoJSON")
    return {"report": report_md, "issues": issues_csv, "flagged": flagged}
