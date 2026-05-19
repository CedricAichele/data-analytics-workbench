from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from app.services.project_backup import (
    build_project_backup_zip,
    deserialize_project_state,
    load_project_backup_zip,
    safe_project_filename,
)
from app.services.quality_score import calculate_quality_score


def test_project_backup_zip_contains_expected_business_files():
    working_df = pd.DataFrame({"customer": ["A", "B"], "revenue": [100, 200]})
    active_dataset = {
        "name": "Sales dataset",
        "working_df": working_df,
        "metadata": {"source": "upload", "file_type": "csv"},
        "transformation_log": ["Rename column: sales -> revenue"],
        "template_mappings": {"sales_retail": {"customer_id": "customer"}},
    }

    backup_bytes = build_project_backup_zip(
        project_metadata={"project_name": "Monthly Sales Review", "analysis_goal": "Review revenue"},
        active_dataset=active_dataset,
        quality_report=calculate_quality_score(working_df),
    )

    with ZipFile(BytesIO(backup_bytes), mode="r") as backup:
        names = set(backup.namelist())

    assert {
        "project_state.json",
        "project_metadata.json",
        "dataset_metadata.json",
        "transformation_log.json",
        "column_mappings.json",
        "quality_summary.json",
        "data_dictionary.xlsx",
        "data_quality_report.xlsx",
        "cleaned_dataset.csv",
        "README_Project_Backup.txt",
    }.issubset(names)


def test_project_backup_can_be_loaded_with_cleaned_dataset():
    working_df = pd.DataFrame({"customer": ["A"], "revenue": [100]})
    active_dataset = {
        "name": "Sales dataset",
        "working_df": working_df,
        "metadata": {"source": "upload", "file_type": "csv"},
        "transformation_log": ["Filter rows: revenue > 0"],
        "template_mappings": {"sales_retail": {"customer_id": "customer"}},
    }
    backup_bytes = build_project_backup_zip(
        project_metadata={"project_name": "Sales Review"},
        active_dataset=active_dataset,
        include_cleaned_dataset=True,
    )

    loaded = load_project_backup_zip(backup_bytes)
    restored = deserialize_project_state(loaded)

    assert loaded.project_metadata["project_name"] == "Sales Review"
    assert loaded.cleaned_dataset is not None
    assert loaded.cleaned_dataset.columns.tolist() == ["customer", "revenue"]
    assert restored["has_cleaned_dataset"] is True
    assert "Restored the cleaned working dataset" in loaded.messages[0]


def test_project_backup_load_without_dataset_has_clear_message():
    backup_bytes = build_project_backup_zip(
        project_metadata={"project_name": "Metadata Only"},
        active_dataset=None,
        include_cleaned_dataset=False,
    )

    loaded = load_project_backup_zip(backup_bytes)

    assert loaded.cleaned_dataset is None
    assert "Please upload the source dataset again" in loaded.messages[0]


def test_safe_project_filename_is_business_friendly():
    assert safe_project_filename("Monthly Sales Review!") == "monthly_sales_review_project_backup.zip"

