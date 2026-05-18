from app.config import RETAIL_TEMPLATE_NAME
from app.services.schema_detector import detect_retail_schema, detect_template_schema


def test_detect_retail_schema_with_synonyms():
    columns = ["InvoiceNo", "InvoiceDate", "Client_ID", "Description", "Qty", "Sales_Price", "Market"]

    result = detect_retail_schema(columns)

    assert result.detected_template == RETAIL_TEMPLATE_NAME
    assert result.confidence_score == 100
    assert result.matched_fields["order_id"] == "InvoiceNo"
    assert result.matched_fields["product_name"] == "Description"
    assert not result.requires_manual_mapping


def test_detect_retail_schema_requires_mapping_when_fields_missing():
    columns = ["date", "product", "sales"]

    result = detect_retail_schema(columns)

    assert result.detected_template is None
    assert result.requires_manual_mapping
    assert "customer_id" in result.missing_fields


def test_detect_manufacturing_schema_with_synonyms():
    columns = ["event_time", "asset_id", "units_produced", "defect_count", "down_minutes", "crew"]

    result = detect_template_schema("manufacturing", columns)

    assert result.detected_template == "Manufacturing Analytics"
    assert result.confidence_score == 100
    assert result.matched_fields["machine_id"] == "asset_id"
    assert result.matched_fields["actual_output"] == "units_produced"


def test_detect_logistics_and_finance_schemas():
    logistics = detect_template_schema("logistics", ["tracking_id", "ship_date", "arrival_date", "promised_date"])
    finance = detect_template_schema("finance", ["journal_id", "posting_date", "transaction_amount", "entry_type"])

    assert logistics.detected_template == "Logistics Analytics"
    assert finance.detected_template == "Finance Analytics"
