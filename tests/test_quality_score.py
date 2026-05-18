import pandas as pd

from app.config import RETAIL_REQUIRED_FIELDS
from app.services.quality_score import calculate_quality_score


def test_quality_score_is_explainable_and_penalizes_issues():
    df = pd.DataFrame(
        {
            "order_id": ["1", "1", "2"],
            "order_date": ["2024-01-01", "not-a-date", "2024-01-03"],
            "customer_id": ["C1", "C1", None],
            "product_name": ["A", "A", "B"],
            "quantity": [1, 1, 0],
            "unit_price": [10, 10, 0],
        }
    )
    mapping = {column: column for column in df.columns}

    report = calculate_quality_score(
        df,
        mapping=mapping,
        required_fields=RETAIL_REQUIRED_FIELDS,
        date_fields=["order_date"],
        numeric_fields=["quantity", "unit_price"],
    )

    assert report.overall_score < 100
    assert report.sub_scores["schema_completeness"] == 100
    assert report.metrics["date_parse_failures"] == 1
    assert report.metrics["invalid_numeric_count"] == 2
    assert report.recommended_fixes


def test_generic_quality_score_does_not_claim_schema_completeness():
    df = pd.DataFrame({"name": ["A", None], "value": [1, 2]})

    report = calculate_quality_score(df)

    assert "schema_completeness" not in report.sub_scores
    assert any("not assessed" in explanation for explanation in report.explanations)
