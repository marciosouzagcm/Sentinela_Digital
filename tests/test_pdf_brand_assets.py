from pathlib import Path

from pdf_generator import resolve_brand_asset_path, _coverage_incomplete


def test_resolve_brand_asset_path_finds_repo_logo():
    asset = resolve_brand_asset_path()
    assert asset is not None
    assert Path(asset).name == "IMG-20260909-WA6745.jpg"


def test_coverage_incomplete_detects_more_than_half_failed_tools():
    report = {
        "coverage_summary": {
            "total_tools": 4,
            "status_counts": {
                "success": 1,
                "unavailable": 2,
                "error": 1,
            },
        }
    }
    assert _coverage_incomplete(report) is True
