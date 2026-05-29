import pandas as pd
from pandas.testing import assert_frame_equal

from app.services.quality_rules import build_quality_issue_rows, run_template_quality_rules, summarize_rule_severity


def test_sales_quality_rules_report_mapped_field_issues_without_mutating_input():
    df = pd.DataFrame(
        {
            "date": ["bad-date", "2026-01-01"],
            "qty": [0, -2],
            "price": [0, 10],
            "customer": [None, "C-1"],
            "product": ["", "Widget"],
        }
    )
    before = df.copy(deep=True)

    rules = run_template_quality_rules(
        df,
        "sales_retail",
        {
            "order_date": "date",
            "quantity": "qty",
            "unit_price": "price",
            "customer_id": "customer",
            "product_name": "product",
        },
    )

    assert_frame_equal(df, before)
    assert set(rules["rule_name"]).issuperset(
        {
            "order_date missing or invalid",
            "quantity equals zero",
            "negative quantity potential return",
            "unit_price <= 0",
            "missing customer_id",
            "missing product_name",
        }
    )
    assert summarize_rule_severity(rules)["critical"] >= 2


def test_manufacturing_quality_rules_report_operational_issues():
    df = pd.DataFrame(
        {
            "timestamp": [None, "2026-01-01"],
            "machine": ["", "M-1"],
            "actual": [10, -1],
            "scrap": [11, 0],
            "downtime": [-5, 3],
            "planned": [0, 20],
        }
    )

    rules = run_template_quality_rules(
        df,
        "manufacturing",
        {
            "timestamp": "timestamp",
            "machine_id": "machine",
            "actual_output": "actual",
            "scrap_count": "scrap",
            "downtime_minutes": "downtime",
            "planned_output": "planned",
        },
    )

    assert "scrap_count > actual_output" in rules["rule_name"].tolist()
    assert "downtime_minutes < 0" in rules["rule_name"].tolist()
    assert "planned_output <= 0" in rules["rule_name"].tolist()


def test_logistics_quality_rules_report_delivery_issues():
    df = pd.DataFrame(
        {
            "order": ["2026-01-05", "2026-01-01"],
            "delivery": ["2026-01-03", None],
            "planned": [None, "2026-01-04"],
            "cost": [-1, 20],
            "carrier": ["", "Roadline"],
        }
    )

    rules = run_template_quality_rules(
        df,
        "logistics",
        {
            "order_date": "order",
            "delivery_date": "delivery",
            "planned_delivery_date": "planned",
            "shipping_cost": "cost",
            "carrier": "carrier",
        },
    )

    assert "delivery_date before order_date" in rules["rule_name"].tolist()
    assert "missing delivery_date" in rules["rule_name"].tolist()
    assert "shipping_cost < 0" in rules["rule_name"].tolist()


def test_finance_quality_rules_report_interpretation_issues():
    df = pd.DataFrame(
        {
            "transaction_date": ["2026-01-01", None, "bad-date"],
            "amount": ["bad", 0, None],
            "type": ["revenue", "unknown", ""],
            "budget": ["100", "not numeric", "50"],
            "actual": ["90", "80", "not numeric"],
        }
    )

    rules = run_template_quality_rules(
        df,
        "finance",
        {
            "date": "transaction_date",
            "amount": "amount",
            "type": "type",
            "budget": "budget",
            "actual": "actual",
        },
    )

    assert "amount missing or non-numeric" in rules["rule_name"].tolist()
    assert "amount equals zero" in rules["rule_name"].tolist()
    assert "type not interpretable as revenue or cost" in rules["rule_name"].tolist()
    assert "budget and actual non-numeric" in rules["rule_name"].tolist()


def test_quality_issue_rows_export_includes_rule_metadata_and_source_rows():
    df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02"],
            "qty": [0, 2],
            "price": [10, -1],
        }
    )
    mapping = {"order_date": "date", "quantity": "qty", "unit_price": "price"}

    affected = build_quality_issue_rows(df, "sales_retail", mapping, rule_name="unit_price <= 0")

    assert affected["rule_name"].tolist() == ["unit_price <= 0"]
    assert affected["severity"].tolist() == ["critical"]
    assert affected["source_row_index"].tolist() == [1]
    assert affected["price"].tolist() == [-1]
