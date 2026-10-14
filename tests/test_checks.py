import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from polyqa import Config, run_qa
from polyqa.synthetic import BBOX, make_plots

CFG = Config(bbox=BBOX)
PARTNERS = {"P001", "P005"}  # clean plots that a planted fault points at


@pytest.fixture(scope="module")
def result():
    plots, faults = make_plots()
    work, issues, dataset_issues = run_qa(plots, CFG)
    return plots, faults, work, issues, dataset_issues


def rows_for(work, plot_id):
    if plot_id is None:
        return work[work["plot_id"].isna()]
    return work[work["plot_id"] == plot_id]


def test_every_planted_fault_is_caught(result):
    _, faults, work, _, _ = result
    for plot_id, check in faults.items():
        rows = rows_for(work, plot_id)
        assert rows[f"flag_{check}"].any(), f"{check} not flagged for {plot_id}"


def test_missing_id_is_caught(result):
    _, _, work, _, _ = result
    assert work["plot_id"].isna().sum() == 1
    assert work.loc[work["plot_id"].isna(), "flag_missing_id"].all()


def test_clean_plots_are_not_flagged(result):
    _, faults, work, _, _ = result
    clean = work[work["plot_id"].astype(str).str.match(r"^P\d{3}$") & ~work["plot_id"].isin(PARTNERS)]
    assert len(clean) == 58
    assert (clean["qa_status"] == "ok").all()


def test_overlap_pair_is_flagged_together(result):
    _, _, work, _, _ = result
    pair = work[work["plot_id"].isin(["F_overlap_a", "F_overlap_b"])]
    assert pair["flag_overlap"].all()


def test_rows_are_never_dropped(result):
    plots, _, work, _, _ = result
    assert len(work) == len(plots)


def test_missing_crs_is_reported():
    gdf = gpd.GeoDataFrame({"plot_id": ["a"], "geometry": [Polygon([(0, 0), (0, 1), (1, 1)])]})
    _, _, dataset_issues = run_qa(gdf, Config())
    assert any(d["check"] == "crs_missing" for d in dataset_issues)


def test_other_crs_is_reprojected_and_reported():
    plots, _ = make_plots(n_clean=10)
    utm = plots.to_crs(plots.estimate_utm_crs())
    _, _, dataset_issues = run_qa(utm, Config())
    assert any(d["check"] == "crs_unexpected" for d in dataset_issues)


def test_issue_table_has_severity(result):
    _, _, _, issues, _ = result
    assert set(issues["severity"]) <= {"error", "warning"}
    assert {"error", "warning"} <= set(issues["severity"])
