"""Lightweight in-session dataset workspace helpers."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any
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
