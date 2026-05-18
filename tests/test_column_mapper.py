from app.services.column_mapper import initialize_retail_mapping, validate_retail_mapping
from app.services.schema_detector import detect_retail_schema


def test_initialize_mapping_uses_schema_detection():
    columns = ["order_id", "order_date", "customer_id", "product_name", "quantity", "unit_price"]
    detection = detect_retail_schema(columns)

    mapping = initialize_retail_mapping(columns, detection)

    assert mapping["order_id"] == "order_id"
    assert mapping["unit_price"] == "unit_price"


def test_validate_mapping_rejects_missing_and_duplicate_columns():
    columns = ["order_id", "order_date", "customer_id", "product_name", "quantity", "unit_price"]
    mapping = {
        "order_id": "order_id",
        "order_date": "order_date",
        "customer_id": "customer_id",
        "product_name": "product_name",
        "quantity": "quantity",
        "unit_price": "quantity",
        "country": None,
        "product_category": None,
        "invoice_status": None,
    }

    validation = validate_retail_mapping(mapping, columns)

    assert not validation.is_valid
    assert validation.duplicate_source_columns == ["quantity"]

