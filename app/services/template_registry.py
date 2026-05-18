"""Registry of generic and domain-specific analytics templates."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import (
    MANUFACTURING_OPTIONAL_FIELDS,
    MANUFACTURING_REQUIRED_FIELDS,
    RETAIL_OPTIONAL_FIELDS,
    RETAIL_REQUIRED_FIELDS,
    SAMPLE_MANUFACTURING_PATH,
    SAMPLE_RETAIL_PATH,
)


@dataclass(frozen=True)
class AnalyticsTemplate:
    template_id: str
    name: str
    status: str
    purpose: str
    required_fields: list[str]
    optional_fields: list[str]
    synonyms: dict[str, list[str]]
    sample_dataset: str | None
    implemented_page: str | None
    when_to_use: str
    mapping_required: bool
    notes: str


GENERIC_TEMPLATE = AnalyticsTemplate(
    template_id="generic",
    name="Generic Analytics",
    status="Always available",
    purpose="Explore any supported tabular dataset without assuming business meaning.",
    required_fields=[],
    optional_fields=[],
    synonyms={},
    sample_dataset=None,
    implemented_page="app/pages/6_generic_analytics.py",
    when_to_use="Use when no domain template fits or before deciding which KPI model applies.",
    mapping_required=False,
    notes="Works on the current working dataframe and preserves all columns.",
)


SALES_RETAIL_SYNONYMS: dict[str, list[str]] = {
    "order_id": ["order_id", "invoice_no", "invoice", "order", "transaction_id"],
    "order_date": ["order_date", "invoice_date", "date", "timestamp"],
    "customer_id": ["customer_id", "customer", "client_id", "user_id"],
    "product_name": ["product_name", "description", "item", "product"],
    "quantity": ["quantity", "qty", "units", "amount"],
    "unit_price": ["unit_price", "price", "sales_price", "item_price"],
    "country": ["country", "region", "market"],
    "product_category": ["product_category", "category", "department", "segment"],
    "invoice_status": ["invoice_status", "status", "order_status"],
}


MANUFACTURING_SYNONYMS: dict[str, list[str]] = {
    "timestamp": ["timestamp", "date", "datetime", "production_date", "event_time", "shift_date"],
    "machine_id": ["machine_id", "machine", "asset_id", "equipment_id", "work_center", "station"],
    "actual_output": ["actual_output", "output", "units_produced", "produced_units", "good_units"],
    "scrap_count": ["scrap_count", "scrap", "defects", "defect_count", "rejected_units"],
    "downtime_minutes": ["downtime_minutes", "downtime", "down_minutes", "stoppage_minutes"],
    "planned_output": ["planned_output", "target_output", "planned_units", "target_units"],
    "runtime_minutes": ["runtime_minutes", "runtime", "run_minutes", "operating_minutes"],
    "line": ["line", "production_line", "cell", "area"],
    "shift": ["shift", "shift_name", "crew"],
    "product": ["product", "sku", "item", "part_number"],
    "quality_status": ["quality_status", "status", "inspection_status"],
}


LOGISTICS_SYNONYMS: dict[str, list[str]] = {
    "shipment_id": ["shipment_id", "shipment", "tracking_id", "consignment_id"],
    "order_date": ["order_date", "ship_date", "dispatch_date", "date"],
    "delivery_date": ["delivery_date", "delivered_at", "arrival_date"],
    "planned_delivery_date": ["planned_delivery_date", "promised_date", "expected_delivery_date", "due_date"],
    "carrier": ["carrier", "shipping_provider", "courier"],
    "origin": ["origin", "ship_from", "warehouse"],
    "destination": ["destination", "ship_to", "market"],
    "shipping_cost": ["shipping_cost", "freight_cost", "cost"],
    "delivery_status": ["delivery_status", "status", "shipment_status"],
}


FINANCE_SYNONYMS: dict[str, list[str]] = {
    "transaction_id": ["transaction_id", "transaction", "entry_id", "journal_id"],
    "date": ["date", "transaction_date", "posting_date", "timestamp"],
    "amount": ["amount", "value", "transaction_amount"],
    "type": ["type", "transaction_type", "revenue_cost_flag", "entry_type"],
    "category": ["category", "expense_category", "revenue_category"],
    "account": ["account", "account_name", "ledger_account"],
    "cost_center": ["cost_center", "department", "business_unit"],
    "budget": ["budget", "planned", "budget_amount"],
    "actual": ["actual", "actual_amount", "realized_amount"],
}


TEMPLATES: dict[str, AnalyticsTemplate] = {
    "generic": GENERIC_TEMPLATE,
    "sales_retail": AnalyticsTemplate(
        template_id="sales_retail",
        name="Sales / Retail Analytics",
        status="Implemented",
        purpose="Calculate sales KPIs, product/customer performance, and RFM segmentation.",
        required_fields=RETAIL_REQUIRED_FIELDS,
        optional_fields=RETAIL_OPTIONAL_FIELDS,
        synonyms=SALES_RETAIL_SYNONYMS,
        sample_dataset=str(SAMPLE_RETAIL_PATH),
        implemented_page="app/pages/5_retail_analytics.py",
        when_to_use="Use for order, invoice, ecommerce, or retail transaction datasets.",
        mapping_required=True,
        notes="KPI logic uses mapped fields only; extra columns remain in the working dataframe.",
    ),
    "manufacturing": AnalyticsTemplate(
        template_id="manufacturing",
        name="Manufacturing Analytics",
        status="Implemented",
        purpose="Analyze production output, scrap, downtime, attainment, and machine performance.",
        required_fields=MANUFACTURING_REQUIRED_FIELDS,
        optional_fields=MANUFACTURING_OPTIONAL_FIELDS,
        synonyms=MANUFACTURING_SYNONYMS,
        sample_dataset=str(SAMPLE_MANUFACTURING_PATH),
        implemented_page="app/pages/8_manufacturing_analytics.py",
        when_to_use="Use for production logs, machine shift summaries, or operations datasets.",
        mapping_required=True,
        notes="Simplified OEE is shown only when the required input fields exist and is labeled as an approximation.",
    ),
    "logistics": AnalyticsTemplate(
        template_id="logistics",
        name="Logistics Analytics",
        status="Planned",
        purpose="Future shipment lead-time, on-time delivery, carrier, and delay analytics.",
        required_fields=["shipment_id", "order_date", "delivery_date", "planned_delivery_date"],
        optional_fields=["carrier", "origin", "destination", "shipping_cost", "delivery_status"],
        synonyms=LOGISTICS_SYNONYMS,
        sample_dataset=None,
        implemented_page=None,
        when_to_use="Use for shipments, delivery operations, and fulfillment performance datasets.",
        mapping_required=True,
        notes="Visible in the template architecture; generic analytics remains available now.",
    ),
    "finance": AnalyticsTemplate(
        template_id="finance",
        name="Finance Analytics",
        status="Planned",
        purpose="Future revenue, cost, margin, and budget variance analytics.",
        required_fields=["transaction_id", "date", "amount", "type"],
        optional_fields=["category", "account", "cost_center", "budget", "actual"],
        synonyms=FINANCE_SYNONYMS,
        sample_dataset=None,
        implemented_page=None,
        when_to_use="Use for finance ledgers, budget extracts, and transactional finance datasets.",
        mapping_required=True,
        notes="Finance interpretation requires an explicit type, category, or sign convention; no guessing is implemented.",
    ),
}


def list_templates(include_generic: bool = True) -> list[AnalyticsTemplate]:
    """Return templates in the intended UI order."""
    ids = ["generic", "sales_retail", "manufacturing", "logistics", "finance"]
    if not include_generic:
        ids.remove("generic")
    return [TEMPLATES[template_id] for template_id in ids]


def get_template(template_id: str) -> AnalyticsTemplate:
    """Return a template definition by id."""
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        raise ValueError(f"Unknown template: {template_id}") from exc


def implemented_domain_templates() -> list[AnalyticsTemplate]:
    """Return implemented domain templates that require mapping."""
    return [
        template
        for template in list_templates(include_generic=False)
        if template.status.lower() == "implemented"
    ]
