from app.services.template_registry import get_template, list_templates


def test_template_registry_contains_expected_templates():
    template_ids = [template.template_id for template in list_templates()]

    assert template_ids == ["generic", "sales_retail", "manufacturing", "logistics", "finance"]
    assert get_template("manufacturing").status == "Implemented"
    assert get_template("logistics").status == "Implemented"
    assert get_template("finance").status == "Implemented"
    assert not get_template("generic").mapping_required
