"""Lightweight in-session dataset workspace helpers."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any
import hashlib
import re

import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class WorkspaceDataset:
    dataset_id: str
    name: str
    raw_df: pd.DataFrame
    working_df: pd.DataFrame
    metadata: dict[str, Any]
    transformation_log: list[str]
    template_mappings: dict[str, dict[str, str | None]]


def _state(state: MutableMapping[str, Any] | None = None) -> MutableMapping[str, Any]:
    return st.session_state if state is None else state


def initialize_workspace(state: MutableMapping[str, Any] | None = None) -> None:
    """Initialize workspace keys and migrate legacy single-dataset state if present."""
    current = _state(state)
    current.setdefault("datasets", {})
    current.setdefault("active_dataset_id", None)

    if current["datasets"] or "raw_df" not in current:
        return

    metadata = dict(current.get("dataset_metadata", {}))
    name = current.get("dataset_name") or metadata.get("file_name") or "Dataset"
    dataset_id = add_dataset(
        name,
        current["raw_df"],
        metadata,
        working_df=current.get("working_df"),
        transformation_log=list(current.get("transformation_log", [])),
        template_mappings=dict(current.get("template_mappings", {})),
        state=current,
        sync=False,
    )
    current["active_dataset_id"] = dataset_id
    sync_legacy_state(current)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "dataset"


def _new_dataset_id(name: str, datasets: dict[str, Any]) -> str:
    base = _slugify(name)
    candidate = base
    suffix = 2
    while candidate in datasets:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def compute_dataset_hash(file_bytes_or_df: bytes | bytearray | pd.DataFrame) -> str:
    """Compute a stable hash for uploaded bytes or a loaded dataframe."""
    if isinstance(file_bytes_or_df, bytes | bytearray):
        return hashlib.sha256(bytes(file_bytes_or_df)).hexdigest()
    if isinstance(file_bytes_or_df, pd.DataFrame):
        df = file_bytes_or_df.copy()
        header = "|".join(f"{column}:{dtype}" for column, dtype in zip(df.columns, df.dtypes)).encode("utf-8")
        values = pd.util.hash_pandas_object(df, index=True).values.tobytes()
        return hashlib.sha256(header + values).hexdigest()
    raise TypeError("compute_dataset_hash expects bytes or a pandas DataFrame.")


def dataset_exists(
    dataset_id_or_hash: str,
    state: MutableMapping[str, Any] | None = None,
) -> bool:
    """Return whether a dataset id or content hash already exists in the workspace."""
    current = _state(state)
    initialize_workspace(current)
    if dataset_id_or_hash in current["datasets"]:
        return True
    return any(
        dataset.get("metadata", {}).get("dataset_hash") == dataset_id_or_hash
        for dataset in current["datasets"].values()
    )


def add_dataset(
    name: str,
    raw_df: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
    *,
    working_df: pd.DataFrame | None = None,
    transformation_log: list[str] | None = None,
    template_mappings: dict[str, dict[str, str | None]] | None = None,
    state: MutableMapping[str, Any] | None = None,
    sync: bool = True,
) -> str:
    """Add a dataset to the workspace and make it active."""
    current = _state(state)
    current.setdefault("datasets", {})
    dataset_id = _new_dataset_id(name, current["datasets"])
    raw_copy = raw_df.copy()
    working_copy = working_df.copy() if working_df is not None else raw_copy.copy()
    dataset = {
        "dataset_id": dataset_id,
        "name": name,
        "raw_df": raw_copy,
        "working_df": working_copy,
        "metadata": dict(metadata or {}),
        "transformation_log": list(transformation_log or []),
        "template_mappings": dict(template_mappings or {}),
        "analytics_results": {},
    }
    current["datasets"][dataset_id] = dataset
    current["active_dataset_id"] = dataset_id
    if sync:
        sync_legacy_state(current)
    return dataset_id


def add_or_activate_dataset(
    name: str,
    raw_df: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
    *,
    dataset_id: str | None = None,
    dataset_hash: str | None = None,
    state: MutableMapping[str, Any] | None = None,
) -> tuple[str, bool]:
    """Add a dataset unless the same id or content hash is already loaded.

    Returns `(dataset_id, created)` where `created` is False when an existing
    dataset was activated instead of adding a duplicate.
    """
    current = _state(state)
    initialize_workspace(current)
    current.setdefault("datasets", {})
    metadata_copy = dict(metadata or {})
    stable_id = dataset_id or metadata_copy.get("dataset_id")
    content_hash = dataset_hash or metadata_copy.get("dataset_hash") or compute_dataset_hash(raw_df)

    if stable_id and stable_id in current["datasets"]:
        current["active_dataset_id"] = stable_id
        sync_legacy_state(current)
        return stable_id, False

    for existing_id, dataset in current["datasets"].items():
        if dataset.get("metadata", {}).get("dataset_hash") == content_hash:
            current["active_dataset_id"] = existing_id
            sync_legacy_state(current)
            return existing_id, False

    metadata_copy["dataset_hash"] = content_hash
    if stable_id:
        metadata_copy["dataset_id"] = stable_id
        raw_copy = raw_df.copy()
        current["datasets"][stable_id] = {
            "dataset_id": stable_id,
            "name": name,
            "raw_df": raw_copy,
            "working_df": raw_copy.copy(),
            "metadata": metadata_copy,
            "transformation_log": [],
            "template_mappings": {},
            "analytics_results": {},
        }
        current["active_dataset_id"] = stable_id
        sync_legacy_state(current)
        return stable_id, True

    created_id = add_dataset(name, raw_df, metadata_copy, state=current)
    return created_id, True


def list_datasets(state: MutableMapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return workspace datasets as lightweight display records."""
    current = _state(state)
    initialize_workspace(current)
    return [
        {
            "dataset_id": dataset_id,
            "name": dataset["name"],
            "metadata": dataset.get("metadata", {}),
            "raw_rows": len(dataset["raw_df"]),
            "raw_columns": len(dataset["raw_df"].columns),
            "working_rows": len(dataset["working_df"]),
            "working_columns": len(dataset["working_df"].columns),
        }
        for dataset_id, dataset in current["datasets"].items()
    ]


def get_loaded_dataset_summary(state: MutableMapping[str, Any] | None = None) -> pd.DataFrame:
    """Return a tabular workspace summary for display and tests."""
    rows = []
    for dataset in list_datasets(state):
        metadata = dataset.get("metadata", {})
        rows.append(
            {
                "dataset_id": dataset["dataset_id"],
                "name": dataset["name"],
                "source": metadata.get("source", "dataset"),
                "file_type": metadata.get("file_type", "data"),
                "raw_shape": f"{dataset['raw_rows']:,} x {dataset['raw_columns']:,}",
                "working_shape": f"{dataset['working_rows']:,} x {dataset['working_columns']:,}",
            }
        )
    return pd.DataFrame(rows)


def set_active_dataset(dataset_id: str, state: MutableMapping[str, Any] | None = None) -> None:
    """Set the active dataset and synchronize legacy state keys."""
    current = _state(state)
    initialize_workspace(current)
    if dataset_id not in current["datasets"]:
        raise ValueError(f"Unknown dataset id: {dataset_id}")
    current["active_dataset_id"] = dataset_id
    sync_legacy_state(current)


def get_active_dataset(state: MutableMapping[str, Any] | None = None) -> dict[str, Any] | None:
    """Return the active dataset dictionary."""
    current = _state(state)
    initialize_workspace(current)
    dataset_id = current.get("active_dataset_id")
    if not dataset_id:
        return None
    return current["datasets"].get(dataset_id)


def get_active_raw_df(state: MutableMapping[str, Any] | None = None) -> pd.DataFrame | None:
    dataset = get_active_dataset(state)
    return None if dataset is None else dataset["raw_df"]


def get_active_working_df(state: MutableMapping[str, Any] | None = None) -> pd.DataFrame | None:
    dataset = get_active_dataset(state)
    return None if dataset is None else dataset["working_df"]


def update_active_working_df(df: pd.DataFrame, state: MutableMapping[str, Any] | None = None) -> None:
    """Replace active working dataframe and synchronize legacy keys."""
    current = _state(state)
    dataset = get_active_dataset(current)
    if dataset is None:
        raise ValueError("No active dataset is available.")
    dataset["working_df"] = df.copy()
    dataset["analytics_results"] = {}
    sync_legacy_state(current)


def get_active_metadata(state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    dataset = get_active_dataset(state)
    return {} if dataset is None else dataset.get("metadata", {})


def get_active_transformation_log(state: MutableMapping[str, Any] | None = None) -> list[str]:
    dataset = get_active_dataset(state)
    return [] if dataset is None else dataset.setdefault("transformation_log", [])


def append_active_transformation_log(entry: str, state: MutableMapping[str, Any] | None = None) -> None:
    dataset = get_active_dataset(state)
    if dataset is None:
        raise ValueError("No active dataset is available.")
    dataset.setdefault("transformation_log", []).append(entry)
    sync_legacy_state(_state(state))


def reset_active_working_df(state: MutableMapping[str, Any] | None = None) -> None:
    dataset = get_active_dataset(state)
    if dataset is None:
        raise ValueError("No active dataset is available.")
    dataset["working_df"] = dataset["raw_df"].copy()
    dataset["transformation_log"] = []
    dataset["template_mappings"] = {}
    dataset["analytics_results"] = {}
    sync_legacy_state(_state(state))


def remove_dataset(dataset_id: str, state: MutableMapping[str, Any] | None = None) -> None:
    current = _state(state)
    initialize_workspace(current)
    if dataset_id not in current["datasets"]:
        return
    del current["datasets"][dataset_id]
    if current.get("active_dataset_id") == dataset_id:
        current["active_dataset_id"] = next(iter(current["datasets"]), None)
    sync_legacy_state(current)


def get_active_template_mapping(
    template_id: str,
    state: MutableMapping[str, Any] | None = None,
) -> dict[str, str | None] | None:
    dataset = get_active_dataset(state)
    if dataset is None:
        return None
    return dataset.setdefault("template_mappings", {}).get(template_id)


def set_active_template_mapping(
    template_id: str,
    mapping: dict[str, str | None],
    state: MutableMapping[str, Any] | None = None,
) -> None:
    dataset = get_active_dataset(state)
    if dataset is None:
        raise ValueError("No active dataset is available.")
    dataset.setdefault("template_mappings", {})[template_id] = dict(mapping)
    dataset["analytics_results"] = {}
    sync_legacy_state(_state(state))


def set_active_analytics_result(
    key: str,
    value: Any,
    state: MutableMapping[str, Any] | None = None,
) -> None:
    """Store an analytics result on the active dataset and legacy session state."""
    current = _state(state)
    dataset = get_active_dataset(current)
    if dataset is None:
        raise ValueError("No active dataset is available.")
    dataset.setdefault("analytics_results", {})[key] = value
    current[key] = value


def get_active_analytics_result(
    key: str,
    state: MutableMapping[str, Any] | None = None,
) -> Any | None:
    """Return an analytics result associated with the active dataset."""
    dataset = get_active_dataset(state)
    if dataset is None:
        return None
    return dataset.setdefault("analytics_results", {}).get(key)


def clear_active_template_state(state: MutableMapping[str, Any] | None = None) -> None:
    dataset = get_active_dataset(state)
    if dataset is None:
        return
    dataset["template_mappings"] = {}
    dataset["analytics_results"] = {}
    sync_legacy_state(_state(state))


def sync_legacy_state(state: MutableMapping[str, Any] | None = None) -> None:
    """Keep old single-dataset session keys aligned with the active dataset."""
    current = _state(state)
    analytics_result_keys = [
        "generic_analytics_result",
        "retail_clean_result",
        "retail_analytics_result",
        "manufacturing_clean_result",
        "manufacturing_analytics_result",
        "logistics_clean_result",
        "logistics_analytics_result",
        "finance_clean_result",
        "finance_analytics_result",
        "retail_controlled_chart_result",
        "manufacturing_controlled_chart_result",
        "logistics_controlled_chart_result",
        "finance_controlled_chart_result",
    ]
    dataset_id = current.get("active_dataset_id")
    dataset = current.get("datasets", {}).get(dataset_id) if dataset_id else None
    if dataset is None:
        for key in [
            "raw_df",
            "working_df",
            "dataset_name",
            "dataset_metadata",
            "transformation_log",
            "template_mappings",
            "column_mapping",
            "manufacturing_mapping",
            "logistics_mapping",
            "finance_mapping",
            *analytics_result_keys,
        ]:
            current.pop(key, None)
        return

    current["raw_df"] = dataset["raw_df"]
    current["working_df"] = dataset["working_df"]
    current["dataset_name"] = dataset["name"]
    current["dataset_metadata"] = dataset.get("metadata", {})
    current["transformation_log"] = dataset.setdefault("transformation_log", [])
    current["template_mappings"] = dataset.setdefault("template_mappings", {})

    template_mappings = current["template_mappings"]
    legacy_keys = {
        "sales_retail": "column_mapping",
        "manufacturing": "manufacturing_mapping",
        "logistics": "logistics_mapping",
        "finance": "finance_mapping",
    }
    for template_id, legacy_key in legacy_keys.items():
        if template_id in template_mappings:
            current[legacy_key] = template_mappings[template_id]
        else:
            current.pop(legacy_key, None)

    for key in analytics_result_keys:
        current.pop(key, None)
    for key, value in dataset.setdefault("analytics_results", {}).items():
        current[key] = value
