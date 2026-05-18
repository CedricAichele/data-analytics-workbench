import pandas as pd

from app.services.logistics_analytics import build_logistics_analytics, clean_logistics_shipments


def _mapping():
    return {
        "shipment_id": "shipment_id",
        "order_date": "order_date",
        "delivery_date": "delivery_date",
        "planned_delivery_date": "planned_delivery_date",
        "carrier": "carrier",
        "origin": "origin",
        "destination": "destination",
        "shipping_cost": "shipping_cost",
        "delivery_status": "delivery_status",
    }


def test_logistics_kpis_and_flags():
    df = pd.DataFrame(
        {
            "shipment_id": ["S1", "S2", "S2", "S3"],
            "order_date": ["2025-01-01", "2025-01-01", "2025-01-01", "2025-01-02"],
            "delivery_date": ["2025-01-03", "2025-01-07", "2025-01-07", None],
            "planned_delivery_date": ["2025-01-04", "2025-01-05", "2025-01-05", "2025-01-04"],
            "carrier": ["A", "B", "B", None],
            "origin": ["X", "X", "X", "Y"],
            "destination": ["D1", "D2", "D2", "D1"],
            "shipping_cost": [100, 200, 200, 150],
            "delivery_status": ["Delivered", "Late", "Late", "Open"],
        }
    )

    clean_result = clean_logistics_shipments(df, _mapping())
    analytics = build_logistics_analytics(clean_result)

    assert analytics.metrics["shipment_count"] == 2
    assert analytics.metrics["delayed_shipments"] == 1
    assert analytics.metrics["on_time_delivery_rate"] == 0.5
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Duplicate rows", "row_count"].iloc[0] == 1
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Missing delivery dates", "row_count"].iloc[0] == 1
