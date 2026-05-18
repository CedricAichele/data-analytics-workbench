import pandas as pd

from app.services.dataset_workspace import (
    add_dataset,
    add_or_activate_dataset,
    append_active_transformation_log,
    compute_dataset_hash,
    dataset_exists,
    get_loaded_dataset_summary,
    get_active_analytics_result,
    get_active_working_df,
    get_active_template_mapping,
    list_datasets,
    reset_active_working_df,
    set_active_dataset,
    set_active_analytics_result,
    set_active_template_mapping,
    update_active_working_df,
)


def test_workspace_adds_and_switches_active_datasets():
    state = {}
    first_id = add_dataset("First", pd.DataFrame({"a": [1, 2]}), {"source": "sample"}, state=state)
    second_id = add_dataset("Second", pd.DataFrame({"b": [3]}), {"source": "upload"}, state=state)

    assert state["active_dataset_id"] == second_id
    assert len(list_datasets(state)) == 2

    set_active_dataset(first_id, state)

    assert get_active_working_df(state).columns.tolist() == ["a"]
    assert state["dataset_name"] == "First"


def test_workspace_updates_working_data_log_and_mapping():
    state = {}
    add_dataset("Dataset", pd.DataFrame({"a": [1, 2, 3]}), {}, state=state)

    update_active_working_df(pd.DataFrame({"a": [1]}), state)
    append_active_transformation_log("Filtered rows", state)
    set_active_template_mapping("finance", {"amount": "a"}, state)

    assert len(get_active_working_df(state)) == 1
    assert state["transformation_log"] == ["Filtered rows"]
    assert get_active_template_mapping("finance", state) == {"amount": "a"}

    reset_active_working_df(state)

    assert len(get_active_working_df(state)) == 3
    assert state["transformation_log"] == []
    assert get_active_template_mapping("finance", state) is None


def test_workspace_keeps_analytics_results_per_active_dataset():
    state = {}
    first_id = add_dataset("First", pd.DataFrame({"a": [1]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "first-result", state)
    second_id = add_dataset("Second", pd.DataFrame({"b": [2]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "second-result", state)

    set_active_dataset(first_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) == "first-result"
    assert state["generic_analytics_result"] == "first-result"

    set_active_dataset(second_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) == "second-result"
    assert state["generic_analytics_result"] == "second-result"


def test_sample_dataset_duplicate_activates_existing_dataset():
    state = {}
    df = pd.DataFrame({"a": [1, 2]})

    first_id, first_created = add_or_activate_dataset(
        "Retail sample",
        df,
        {"source": "sample", "dataset_id": "sample-retail-orders"},
        dataset_id="sample-retail-orders",
        state=state,
    )
    second_id, second_created = add_or_activate_dataset(
        "Retail sample",
        df,
        {"source": "sample", "dataset_id": "sample-retail-orders"},
        dataset_id="sample-retail-orders",
        state=state,
    )

    assert first_created is True
    assert second_created is False
    assert first_id == second_id == "sample-retail-orders"
    assert len(list_datasets(state)) == 1


def test_same_upload_content_activates_existing_dataset_even_with_different_name():
    state = {}
    df = pd.DataFrame({"a": [1, 2]})
    first_id, first_created = add_or_activate_dataset("first.csv", df, {"source": "upload"}, state=state)
    second_id, second_created = add_or_activate_dataset("second.csv", df.copy(), {"source": "upload"}, state=state)

    assert first_created is True
    assert second_created is False
    assert first_id == second_id
    assert len(list_datasets(state)) == 1


def test_same_filename_different_content_creates_separate_dataset():
    state = {}
    first_id, _ = add_or_activate_dataset("upload.csv", pd.DataFrame({"a": [1]}), {"source": "upload"}, state=state)
    second_id, created = add_or_activate_dataset("upload.csv", pd.DataFrame({"a": [2]}), {"source": "upload"}, state=state)

    assert created is True
    assert first_id != second_id
    assert len(list_datasets(state)) == 2


def test_dataset_summary_and_hash_lookup():
    state = {}
    df = pd.DataFrame({"a": [1]})
    dataset_hash = compute_dataset_hash(df)
    add_or_activate_dataset("Dataset", df, {"source": "upload"}, dataset_hash=dataset_hash, state=state)

    assert dataset_exists(dataset_hash, state)
    summary = get_loaded_dataset_summary(state)
    assert summary.loc[0, "working_shape"] == "1 x 1"
