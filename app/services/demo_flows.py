"""Guided demo setup helpers for first-time users."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, MutableMapping
from typing import Any

import streamlit as st

from app.services.data_loader import (
    LoadedDataset,
    load_sample_finance_transactions,
    load_sample_logistics_shipments,
    load_sample_manufacturing_operations,
    load_sample_retail_orders,
)
from app.services.dataset_workspace import add_or_activate_dataset, sync_legacy_state
from app.services.project_state import associate_dataset_with_active_project, create_project
from app.services.schema_detector import detect_retail_schema, detect_template_schema
from app.services.template_registry import implemented_domain_templates


@dataclass(frozen=True)
class DemoFlow:
    template_id: str
    label: str
    project_name: str
    workflow: str
    description: str
    loader: Callable[[], LoadedDataset]


@dataclass(frozen=True)
class DemoFlowResult:
    template_id: str
    project_id: str
    dataset_id: str
    project_created: bool
    dataset_created: bool
    message: str


DEMO_FLOWS: dict[str, DemoFlow] = {
    "sales_retail": DemoFlow(
        template_id="sales_retail",
        label="Sales / Retail Demo",
        project_name="Sales / Retail Demo Project",
        workflow="Domain KPI Analysis",
        description="Recommended first demo for customer, product, order and revenue analytics.",
        loader=load_sample_retail_orders,
    ),
    "manufacturing": DemoFlow(
        template_id="manufacturing",
        label="Manufacturing Demo",
        project_name="Manufacturing Demo Project",
        workflow="Domain KPI Analysis",
        description="Review production output, downtime, scrap and machine performance analytics.",
        loader=load_sample_manufacturing_operations,
    ),
    "logistics": DemoFlow(
        template_id="logistics",
        label="Logistics Demo",
        project_name="Logistics Demo Project",
        workflow="Domain KPI Analysis",
        description="Review shipment lead time, delays, carrier and destination performance.",
        loader=load_sample_logistics_shipments,
    ),
    "finance": DemoFlow(
        template_id="finance",
        label="Finance Demo",
        project_name="Finance Demo Project",
        workflow="Domain KPI Analysis",
        description="Review revenue, cost, margin, variance and transaction analytics.",
        loader=load_sample_finance_transactions,
    ),
}


def start_guided_demo(template_id: str, state: MutableMapping[str, Any] | None = None) -> DemoFlowResult:
    """Create or activate a demo project and matching sample dataset."""
    if template_id not in DEMO_FLOWS:
        raise ValueError(f"Unknown demo flow: {template_id}")

    current = st.session_state if state is None else state
    demo = DEMO_FLOWS[template_id]
    loaded = demo.loader()
    loaded.metadata["suggested_template"] = template_id

    project_id, project_created = create_project(
        {
            "project_name": demo.project_name,
            "project_description": demo.description,
            "analysis_goal": f"Explore the {demo.label} workflow with bundled sample data.",
            "selected_workflow": demo.workflow,
            "suggested_template": _template_label(template_id),
            "desired_outputs": ["Data Quality Report", "Data Dictionary", "KPI Analysis", "BI-ready Export Package"],
            "notes": "Created by guided demo setup.",
        },
        state=current,
    )
    dataset_id, dataset_created = add_or_activate_dataset(
        loaded.metadata.get("file_name", demo.label),
        loaded.dataframe,
        loaded.metadata,
        dataset_id=loaded.metadata.get("dataset_id"),
        state=current,
    )
    associate_dataset_with_active_project(dataset_id, current)
    _store_detections(list(loaded.dataframe.columns), template_id, current)
    sync_legacy_state(current)

    project_action = "Created" if project_created else "Activated"
    dataset_action = "loaded" if dataset_created else "activated"
    return DemoFlowResult(
        template_id=template_id,
        project_id=project_id,
        dataset_id=dataset_id,
        project_created=project_created,
        dataset_created=dataset_created,
        message=f"{project_action} {demo.label} and {dataset_action} the matching sample dataset.",
    )


def list_demo_flows() -> list[DemoFlow]:
    """Return demos in the preferred user-facing order."""
    return [DEMO_FLOWS[key] for key in ["sales_retail", "manufacturing", "logistics", "finance"]]


def _store_detections(columns: list[str], selected_template_id: str, state: MutableMapping[str, Any]) -> None:
    detections = {
        template.template_id: detect_template_schema(template.template_id, columns)
        for template in implemented_domain_templates()
    }
    state["template_schema_detections"] = detections
    state["retail_schema_detection"] = detections.get("sales_retail") or detect_retail_schema(columns)
    for template_id, detection in detections.items():
        state[f"{template_id}_schema_detection"] = detection
    state["selected_template_id"] = selected_template_id


def _template_label(template_id: str) -> str:
    return {
        "sales_retail": "Sales / Retail",
        "manufacturing": "Manufacturing",
        "logistics": "Logistics",
        "finance": "Finance",
    }.get(template_id, "Generic")
