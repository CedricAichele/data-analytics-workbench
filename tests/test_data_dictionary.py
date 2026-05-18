import pandas as pd

from app.services.data_dictionary import generate_data_dictionary


def test_generate_data_dictionary_includes_missing_numeric_date_and_mapping_details():
    df = pd.DataFrame(
        {
            "order_id": ["A-1", "A-2", "A-3"],
            "quantity": [2, 0, -1],
            "order_date": pd.to_datetime(["2026-01-01", "2026-01-05", "2026-01-09"]),
            "category": ["Books", None, "Games"],
        }
    )

    dictionary = generate_data_dictionary(
        df,
        template_mappings={
            "sales_retail": {
                "order_id": "order_id",
                "quantity": "quantity",
                "order_date": "order_date",
            }
        },
    )

    quantity = dictionary[dictionary["column_name"] == "quantity"].iloc[0]
    assert quantity["detected_data_type"] == "numeric"
    assert quantity["numeric_min"] == -1
    assert quantity["numeric_max"] == 2
    assert "Numeric column with zero or negative values" in quantity["quality_notes"]
    assert "Sales / Retail Analytics: quantity" in quantity["mapped_business_field"]

    order_date = dictionary[dictionary["column_name"] == "order_date"].iloc[0]
    assert order_date["detected_data_type"] == "datetime"
    assert order_date["first_date"] == "2026-01-01"
    assert order_date["last_date"] == "2026-01-09"

    category = dictionary[dictionary["column_name"] == "category"].iloc[0]
    assert category["missing_value_count"] == 1
    assert category["missing_value_percentage"] == 33.33
    assert "Contains missing values" in category["quality_notes"]

