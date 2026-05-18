import pandas as pd

from app.services.finance_analytics import build_finance_analytics, clean_finance_transactions


def _mapping():
    return {
        "transaction_id": "transaction_id",
        "date": "date",
        "amount": "amount",
        "type": "type",
        "category": "category",
        "account": "account",
        "cost_center": "cost_center",
        "budget": "budget",
        "actual": "actual",
    }


def test_finance_kpis_and_type_validation():
    df = pd.DataFrame(
        {
            "transaction_id": ["T1", "T2", "T2", "T3", "T4"],
            "date": ["2025-01-01", "2025-01-02", "2025-01-02", "2025-01-03", "2025-01-04"],
            "amount": [1000, 250, 250, 0, 75],
            "type": ["revenue", "cost", "cost", "cost", "unknown"],
            "category": ["Sales", "Software", "Software", None, "Other"],
            "account": ["A", "B", "B", "C", "D"],
            "cost_center": ["Sales", "Ops", "Ops", "Ops", "Finance"],
            "budget": [900, 200, 200, 100, 50],
            "actual": [1000, 250, 250, 0, 75],
        }
    )

    clean_result = clean_finance_transactions(df, _mapping())
    analytics = build_finance_analytics(clean_result)

    assert analytics.metrics["total_revenue"] == 1000
    assert analytics.metrics["total_cost"] == 250
    assert analytics.metrics["net_result"] == 750
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Duplicate rows", "row_count"].iloc[0] == 1
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Uninterpretable type values", "row_count"].iloc[0] == 1
