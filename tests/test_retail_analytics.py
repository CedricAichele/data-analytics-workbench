import pandas as pd

from app.services.retail_analytics import (
    assign_rfm_segments,
    build_retail_analytics,
    clean_retail_orders,
)


def _mapping():
    return {
        "order_id": "order_id",
        "order_date": "order_date",
        "customer_id": "customer_id",
        "product_name": "product_name",
        "quantity": "quantity",
        "unit_price": "unit_price",
        "country": "country",
        "product_category": "product_category",
        "invoice_status": "invoice_status",
    }


def test_retail_kpis_and_cleaning_pipeline_use_flags():
    df = pd.DataFrame(
        {
            "order_id": ["1001", "1001", "1002", "1003", "1004", "1005"],
            "order_date": ["2024-01-01", "2024-01-01", "2024-01-05", "2024-02-01", "2024-02-03", "2024-02-10"],
            "customer_id": ["C1", "C1", "C2", "C1", None, "C3"],
            "product_name": ["A", "A", "B", "A", "C", "D"],
            "product_category": ["Core", "Core", "Core", "Core", "Other", "Other"],
            "quantity": [2, 2, 1, -1, 1, 2],
            "unit_price": [10, 10, 30, 10, 0, 20],
            "country": ["US", "US", "US", "US", "DE", "DE"],
            "invoice_status": ["Completed", "Completed", "Completed", "Completed", "Completed", "Cancelled"],
        }
    )

    clean_result = clean_retail_orders(df, _mapping())
    analytics = build_retail_analytics(clean_result)

    assert analytics.metrics["net_revenue"] == 50
    assert analytics.metrics["gross_revenue"] == 90
    assert analytics.metrics["number_of_orders"] == 2
    assert analytics.metrics["number_of_customers"] == 2
    assert analytics.metrics["return_rate"] == 0.2
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Duplicate rows", "row_count"].iloc[0] == 1
    assert clean_result.issue_summary.loc[clean_result.issue_summary["issue"] == "Invalid unit prices", "row_count"].iloc[0] == 1
    assert not analytics.customer_rfm.empty


def test_assign_rfm_segments_returns_expected_segment_labels():
    rfm_base = pd.DataFrame(
        {
            "customer_id": [f"C{i}" for i in range(1, 7)],
            "recency_days": [1, 5, 10, 30, 60, 120],
            "frequency": [10, 8, 3, 2, 5, 1],
            "monetary": [1000, 800, 300, 150, 400, 50],
        }
    )

    segmented = assign_rfm_segments(rfm_base)

    assert {"Champions", "Loyal Customers", "Potential Loyalists", "At Risk", "Low Value"} & set(segmented["segment"])
    assert segmented["r_score"].between(1, 5).all()
    assert segmented["f_score"].between(1, 5).all()
    assert segmented["m_score"].between(1, 5).all()
