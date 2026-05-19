import pandas as pd

from app.services.dataset_workspace import (
    add_dataset,
    add_or_activate_dataset,
    analyze_dataset_size,
    append_active_transformation_log,
    clear_all_datasets,
    clear_dataset_results,
    compute_dataset_hash,
    dataset_exists,
    get_active_analytics_result,
    get_active_dataset_summary,
    get_active_working_df,
    get_loaded_dataset_summary,
    get_active_template_mapping,
    list_datasets,
    remove_dataset,
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
    set_active_analytics_result("generic_controlled_chart_result", {"chart_data": "first-chart"}, state)
    second_id = add_dataset("Second", pd.DataFrame({"b": [2]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "second-result", state)
    set_active_analytics_result("generic_controlled_chart_result", {"chart_data": "second-chart"}, state)

    set_active_dataset(first_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) == "first-result"
    assert state["generic_analytics_result"] == "first-result"
    assert get_active_analytics_result("generic_controlled_chart_result", state) == {"chart_data": "first-chart"}
    assert state["generic_controlled_chart_result"] == {"chart_data": "first-chart"}

    set_active_dataset(second_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) == "second-result"
    assert state["generic_analytics_result"] == "second-result"
    assert get_active_analytics_result("generic_controlled_chart_result", state) == {"chart_data": "second-chart"}


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


def test_remove_active_dataset_clears_results_and_selects_next_dataset():
    state = {}
    first_id = add_dataset("First", pd.DataFrame({"a": [1]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "first-result", state)
    second_id = add_dataset("Second", pd.DataFrame({"b": [2]}), {}, state=state)
    set_active_dataset(first_id, state)

    remove_dataset(first_id, state)

    assert first_id not in state["datasets"]
    assert state["active_dataset_id"] == second_id
    assert state.get("generic_analytics_result") is None


def test_clear_all_datasets_keeps_project_state_keys():
    state = {"project_metadata": {"project_name": "Keep Me"}}
    add_dataset("Dataset", pd.DataFrame({"a": [1]}), {}, state=state)

    clear_all_datasets(state)

    assert state["datasets"] == {}
    assert state["active_dataset_id"] is None
    assert "raw_df" not in state
    assert state["project_metadata"]["project_name"] == "Keep Me"


def test_reset_active_working_dataset_clears_stale_results():
    state = {}
    add_dataset("Dataset", pd.DataFrame({"a": [1, 2]}), {}, state=state)
    update_active_working_df(pd.DataFrame({"a": [1]}), state)
    set_active_analytics_result("generic_analytics_result", "stale", state)

    reset_active_working_df(state)

    assert len(get_active_working_df(state)) == 2
    assert get_active_analytics_result("generic_analytics_result", state) is None


def test_clear_dataset_results_scopes_to_requested_dataset():
    state = {}
    first_id = add_dataset("First", pd.DataFrame({"a": [1]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "first", state)
    second_id = add_dataset("Second", pd.DataFrame({"b": [2]}), {}, state=state)
    set_active_analytics_result("generic_analytics_result", "second", state)

    clear_dataset_results(first_id, state)
    set_active_dataset(first_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) is None
    set_active_dataset(second_id, state)
    assert get_active_analytics_result("generic_analytics_result", state) == "second"


def test_large_dataset_guardrail_metadata():
    df = pd.DataFrame({"a": range(3), "b": range(3), "c": range(3)})
    profile = analyze_dataset_size(df, row_threshold=2, column_threshold=10, memory_mb_threshold=100)

    assert profile["is_large_dataset"] is True
    assert "rows" in profile["large_dataset_reasons"][0]


def test_active_dataset_summary_includes_large_dataset_state():
    state = {}
    add_dataset("Dataset", pd.DataFrame({"a": range(3)}), {"source": "upload"}, state=state)

    summary = get_active_dataset_summary(state)

    assert summary["dataset_name"] == "Dataset"
    assert summary["raw_shape"] == "3 x 1"
    assert summary["is_large_dataset"] is False
