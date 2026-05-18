from __future__ import annotations

from datetime import date

import pandas as pd

from app.services.chart_controls import apply_date_range_filter, apply_value_filters, monthly_sum, top_n


def test_apply_date_range_filter_is_inclusive():
    df = pd.DataFrame({"day": pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-10"]), "value": [1, 2, 3]})

    result = apply_date_range_filter(df, "day", date(2026, 1, 5), date(2026, 1, 10))

    assert result["value"].tolist() == [2, 3]


def test_apply_value_filters_ignores_empty_selections():
    df = pd.DataFrame({"category": ["A", "B", "C"], "region": ["North", "South", "North"]})

    result = apply_value_filters(df, {"category": ["A", "C"], "region": []})

    assert result["category"].tolist() == ["A", "C"]


def test_top_n_and_monthly_sum():
    df = pd.DataFrame(
        {
            "month": pd.to_datetime(["2026-01-01", "2026-01-20", "2026-02-01"]),
            "name": ["B", "A", "C"],
            "value": [2, 5, 3],
        }
    )

    assert top_n(df, "value", 2)["name"].tolist() == ["A", "C"]
    monthly = monthly_sum(df, "month", "value")
    assert monthly["value"].tolist() == [7, 3]
