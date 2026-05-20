from app.services.template_recommendations import (
    build_template_recommendations,
    no_dataset_guidance,
    recommend_best_template,
)


def _by_id(recommendations):
    return {item.template_id: item for item in recommendations}


def test_generic_analytics_is_always_available_when_dataset_exists():
    recommendations = build_template_recommendations(["customer", "amount"])
    generic = _by_id(recommendations)["generic"]

    assert generic.status == "Available"
    assert generic.confidence_score == 100.0
    assert generic.mapping_required is False


def test_sales_dataset_recommends_sales_retail():
    recommendations = build_template_recommendations(
        ["order_id", "order_date", "customer_id", "product_name", "quantity", "unit_price", "country"]
    )
    best = recommend_best_template(recommendations)

    assert best is not None
    assert best.template_id == "sales_retail"
    assert best.status == "Recommended"
    assert best.required_missing == []


def test_manufacturing_dataset_recommends_manufacturing():
    recommendations = build_template_recommendations(
        ["timestamp", "machine_id", "actual_output", "scrap_count", "downtime_minutes", "shift"]
    )
    best = recommend_best_template(recommendations)

    assert best is not None
    assert best.template_id == "manufacturing"
    assert best.status == "Recommended"


def test_missing_required_fields_are_reported_for_partial_match():
    recommendations = build_template_recommendations(["order_date", "product_name", "quantity"])
    sales = _by_id(recommendations)["sales_retail"]

    assert sales.status == "Partial match"
    assert "order_id" in sales.required_missing
    assert "customer_id" in sales.required_missing
    assert sales.mapping_required is True
    assert recommend_best_template(recommendations) is None


def test_no_compatible_domain_template_keeps_generic_guidance():
    recommendations = build_template_recommendations(["notes", "owner", "comment"])

    assert recommend_best_template(recommendations) is None
    assert _by_id(recommendations)["generic"].recommended_next_action == "Open Generic Analytics"


def test_no_dataset_returns_safe_guidance():
    assert build_template_recommendations(None) == []
    assert no_dataset_guidance() == "Load a dataset to receive template recommendations."
