import pandas as pd

from app.services.manufacturing_analytics import build_manufacturing_analytics, clean_manufacturing_operations


def _mapping():
    return {
        "timestamp": "timestamp",
        "machine_id": "machine_id",
        "actual_output": "actual_output",
        "scrap_count": "scrap_count",
        "downtime_minutes": "downtime_minutes",
        "planned_output": "planned_output",
        "runtime_minutes": "runtime_minutes",
        "line": "line",
        "shift": "shift",
        "product": "product",
        "quality_status": "quality_status",
    }


def test_manufacturing_kpis_and_issue_flags():
    df = pd.DataFrame(
        {
            "timestamp": ["2025-01-01 06:00", "2025-01-01 06:00", "bad-date", "2025-01-02 06:00"],
            "machine_id": ["M1", "M1", "M2", None],
            "line": ["Line A", "Line A", "Line B", "Line B"],
            "shift": ["Day", "Day", "Night", None],
            "product": ["A", "A", "B", "B"],
            "planned_output": [100, 100, 120, 100],
            "actual_output": [90, 90, 100, 80],
            "scrap_count": [5, 5, 30, 2],
            "downtime_minutes": [10, 10, 20, 5],
            "runtime_minutes": [400, 400, 380, 390],
            "quality_status": ["Pass", "Pass", "Review", "Pass"],
        }
    )

    clean_result = clean_manufacturing_operations(df, _mapping())
    analytics = build_manufacturing_analytics(clean_result)

    assert analytics.metrics["total_output"] == 90
    assert analytics.metrics["total_scrap"] == 5
    assert analytics.metrics["scrap_rate"] == round(5 / 90, 4)
    assert analytics.metrics["simplified_oee_approximation"] is not None
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Duplicate rows", "row_count"].iloc[0] == 1
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Missing machine IDs", "row_count"].iloc[0] == 1
    assert not analytics.machine_performance.empty
