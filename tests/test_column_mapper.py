from app.services.column_mapper import initialize_retail_mapping, validate_retail_mapping, validate_template_mapping
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


def test_validate_mapping_for_all_implemented_templates():
    template_columns = {
        "manufacturing": ["timestamp", "machine_id", "actual_output", "scrap_count", "downtime_minutes"],
        "logistics": ["shipment_id", "order_date", "delivery_date", "planned_delivery_date"],
        "finance": ["transaction_id", "date", "amount", "type"],
    }

    for template_id, columns in template_columns.items():
        mapping = {column: column for column in columns}
        validation = validate_template_mapping(template_id, mapping, columns)
        assert validation.is_valid, template_id
