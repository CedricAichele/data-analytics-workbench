from io import BytesIO

import pytest

from app.services.mapping_profiles import (
    apply_mapping_profile,
    build_mapping_profile_backup,
    import_mapping_profile,
    list_mapping_profiles,
    load_mapping_profile_backup,
    save_mapping_profile,
    validate_mapping_profile,
)


def test_save_and_list_mapping_profile():
    state = {}
    mapping = {"order_id": "order_id", "quantity": "qty"}

    profile_id, created = save_mapping_profile(
        profile_name="Monthly Sales Export",
        template_id="sales_retail",
        mapping=mapping,
        notes="Recurring CRM export",
        state=state,
    )

    assert created is True
    profiles = list_mapping_profiles("sales_retail", state)
    assert profiles[0]["profile_id"] == profile_id
    assert profiles[0]["mapping"] == mapping


def test_mapping_profile_validates_missing_columns():
    profile = {
        "profile_name": "Retail",
        "template_id": "sales_retail",
        "mapping": {"order_id": "invoice", "quantity": "qty"},
    }

    validation = validate_mapping_profile(profile, ["invoice"])

    assert validation.is_valid is False
    assert validation.missing_columns == ["qty"]
    with pytest.raises(ValueError):
        apply_mapping_profile(profile, ["invoice"])


def test_mapping_profile_backup_round_trip_and_duplicate_prevention():
    state = {}
    _, created = save_mapping_profile(
        profile_name="Retail Backup",
        template_id="sales_retail",
        mapping={"order_id": "order_id"},
        state=state,
    )
    assert created is True
    profile = list_mapping_profiles("sales_retail", state)[0]

    backup = build_mapping_profile_backup(profile)
    loaded = load_mapping_profile_backup(BytesIO(backup))
    first_id, first_created = import_mapping_profile(loaded, state)
    second_id, second_created = import_mapping_profile(loaded, state)

    assert first_id == second_id
    assert first_created is False
    assert second_created is False
    assert len(list_mapping_profiles("sales_retail", state)) == 1
