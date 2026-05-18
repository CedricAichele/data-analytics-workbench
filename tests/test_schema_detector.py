from app.config import RETAIL_TEMPLATE_NAME
from app.services.schema_detector import detect_retail_schema


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

