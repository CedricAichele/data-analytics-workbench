"""Template-specific explainable quality rules."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class QualityRuleResult:
    template: str
    rule_name: str
    severity: str
    affected_rows_count: int
    affected_percentage: float
    explanation: str
    recommended_fix: str


def run_template_quality_rules(
    df: pd.DataFrame,
    template_id: str,
    mapping: dict[str, str | None],
) -> pd.DataFrame:
    """Run lightweight template-specific rules without mutating the dataframe."""
    rules = {
        "sales_retail": _sales_rules,
        "manufacturing": _manufacturing_rules,
        "logistics": _logistics_rules,
        "finance": _finance_rules,
    }
    if template_id not in rules:
        return _empty_rules_frame()
    working = df.copy(deep=True)
    results = rules[template_id](working, mapping)
    if not results:
        return _empty_rules_frame()
    return pd.DataFrame([result.__dict__ for result in results])


def summarize_rule_severity(rule_results: pd.DataFrame) -> dict[str, int]:
    """Count template-specific rule severities for UI display."""
    if rule_results.empty:
        return {"critical": 0, "warning": 0, "info": 0}
    counts = rule_results["severity"].value_counts().to_dict()
    return {severity: int(counts.get(severity, 0)) for severity in ["critical", "warning", "info"]}


def build_quality_issue_rows(
    df: pd.DataFrame,
    template_id: str,
    mapping: dict[str, str | None],
    *,
    rule_name: str | None = None,
) -> pd.DataFrame:
    """Return source rows affected by template quality rules without mutating data."""
    masks = _rule_masks(df.copy(deep=True), template_id, mapping)
    rows: list[pd.DataFrame] = []
    for name, details in masks.items():
        if rule_name and name != rule_name:
            continue
        affected = df.loc[details["mask"].fillna(False)].copy()
        if affected.empty:
            continue
        affected.insert(0, "severity", details["severity"])
        affected.insert(0, "rule_name", name)
        affected.insert(0, "source_row_index", affected.index)
        rows.append(affected.reset_index(drop=True))
    if not rows:
        return pd.DataFrame(columns=["source_row_index", "rule_name", "severity", *df.columns])
    return pd.concat(rows, ignore_index=True, sort=False)


def _empty_rules_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "template",
            "rule_name",
            "severity",
            "affected_rows_count",
            "affected_percentage",
            "explanation",
            "recommended_fix",
        ]
    )


def _rule_masks(
    df: pd.DataFrame,
    template_id: str,
    mapping: dict[str, str | None],
) -> dict[str, dict[str, pd.Series | str]]:
    builders = {
        "sales_retail": _sales_rule_masks,
        "manufacturing": _manufacturing_rule_masks,
        "logistics": _logistics_rule_masks,
        "finance": _finance_rule_masks,
    }
    if template_id not in builders:
        return {}
    return builders[template_id](df, mapping)


def _column(mapping: dict[str, str | None], field: str) -> str | None:
    return mapping.get(field)


def _series(df: pd.DataFrame, mapping: dict[str, str | None], field: str) -> pd.Series | None:
    column = _column(mapping, field)
    if not column or column not in df.columns:
        return None
    return df[column]


def _numeric(df: pd.DataFrame, mapping: dict[str, str | None], field: str) -> pd.Series | None:
    series = _series(df, mapping, field)
    if series is None:
        return None
    return pd.to_numeric(series, errors="coerce")


def _date(df: pd.DataFrame, mapping: dict[str, str | None], field: str) -> pd.Series | None:
    series = _series(df, mapping, field)
    if series is None:
        return None
    try:
        return pd.to_datetime(series, errors="coerce", format="mixed")
    except TypeError:
        return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


def _result(
    template: str,
    rule_name: str,
    severity: str,
    mask: pd.Series,
    explanation: str,
    recommended_fix: str,
) -> QualityRuleResult:
    affected = int(mask.fillna(False).sum())
    total = max(len(mask), 1)
    return QualityRuleResult(
        template=template,
        rule_name=rule_name,
        severity=severity,
        affected_rows_count=affected,
        affected_percentage=round(affected / total * 100, 2),
        explanation=explanation,
        recommended_fix=recommended_fix,
    )


def _sales_rules(df: pd.DataFrame, mapping: dict[str, str | None]) -> list[QualityRuleResult]:
    template = "Sales / Retail"
    results: list[QualityRuleResult] = []
    order_date = _date(df, mapping, "order_date")
    if order_date is not None:
        results.append(_result(template, "order_date missing or invalid", "critical", order_date.isna(), "Orders without usable dates cannot support trend analysis.", "Standardize or fill valid order dates."))
    quantity = _numeric(df, mapping, "quantity")
    if quantity is not None:
        results.append(_result(template, "quantity equals zero", "warning", quantity == 0, "Zero-quantity rows do not contribute meaningful sales volume.", "Review whether these rows are corrections, cancelled lines, or data-entry issues."))
        results.append(_result(template, "negative quantity potential return", "info", quantity < 0, "Negative quantities may represent returns.", "Confirm return handling before interpreting net sales."))
    unit_price = _numeric(df, mapping, "unit_price")
    if unit_price is not None:
        results.append(_result(template, "unit_price <= 0", "critical", unit_price <= 0, "Invalid prices distort revenue KPIs.", "Correct prices or exclude invalid transaction lines with an audit trail."))
    customer = _series(df, mapping, "customer_id")
    if customer is not None:
        results.append(_result(template, "missing customer_id", "warning", customer.isna() | customer.astype("string").str.strip().eq(""), "Missing customers weaken customer and RFM analysis.", "Backfill customer IDs where possible or exclude rows from customer-level KPIs."))
    product = _series(df, mapping, "product_name")
    if product is not None:
        results.append(_result(template, "missing product_name", "warning", product.isna() | product.astype("string").str.strip().eq(""), "Missing products weaken product performance reporting.", "Fill or correct product descriptions before product analysis."))
    return results


def _sales_rule_masks(df: pd.DataFrame, mapping: dict[str, str | None]) -> dict[str, dict[str, pd.Series | str]]:
    masks: dict[str, dict[str, pd.Series | str]] = {}
    order_date = _date(df, mapping, "order_date")
    if order_date is not None:
        masks["order_date missing or invalid"] = {"severity": "critical", "mask": order_date.isna()}
    quantity = _numeric(df, mapping, "quantity")
    if quantity is not None:
        masks["quantity equals zero"] = {"severity": "warning", "mask": quantity == 0}
        masks["negative quantity potential return"] = {"severity": "info", "mask": quantity < 0}
    unit_price = _numeric(df, mapping, "unit_price")
    if unit_price is not None:
        masks["unit_price <= 0"] = {"severity": "critical", "mask": unit_price <= 0}
    customer = _series(df, mapping, "customer_id")
    if customer is not None:
        masks["missing customer_id"] = {"severity": "warning", "mask": customer.isna() | customer.astype("string").str.strip().eq("")}
    product = _series(df, mapping, "product_name")
    if product is not None:
        masks["missing product_name"] = {"severity": "warning", "mask": product.isna() | product.astype("string").str.strip().eq("")}
    return masks


def _manufacturing_rules(df: pd.DataFrame, mapping: dict[str, str | None]) -> list[QualityRuleResult]:
    template = "Manufacturing"
    results: list[QualityRuleResult] = []
    actual = _numeric(df, mapping, "actual_output")
    scrap = _numeric(df, mapping, "scrap_count")
    downtime = _numeric(df, mapping, "downtime_minutes")
    planned = _numeric(df, mapping, "planned_output")
    timestamp = _date(df, mapping, "timestamp")
    machine = _series(df, mapping, "machine_id")
    if actual is not None:
        results.append(_result(template, "actual_output < 0", "critical", actual < 0, "Negative output is not valid for production KPIs.", "Correct production output values."))
    if scrap is not None and actual is not None:
        results.append(_result(template, "scrap_count > actual_output", "critical", scrap > actual, "Scrap greater than output indicates a likely data issue.", "Validate scrap and output capture logic."))
    if downtime is not None:
        results.append(_result(template, "downtime_minutes < 0", "critical", downtime < 0, "Negative downtime is not meaningful.", "Correct downtime records before downtime KPIs."))
    if planned is not None:
        results.append(_result(template, "planned_output <= 0", "warning", planned <= 0, "Zero or negative planned output prevents attainment analysis.", "Fill valid planned output or exclude rows from attainment metrics."))
    if machine is not None:
        results.append(_result(template, "missing machine_id", "critical", machine.isna() | machine.astype("string").str.strip().eq(""), "Rows without machine IDs cannot support machine performance reporting.", "Backfill or correct machine identifiers."))
    if timestamp is not None:
        results.append(_result(template, "missing timestamp", "critical", timestamp.isna(), "Rows without timestamps cannot support production trends.", "Standardize production timestamps."))
    return results


def _manufacturing_rule_masks(df: pd.DataFrame, mapping: dict[str, str | None]) -> dict[str, dict[str, pd.Series | str]]:
    masks: dict[str, dict[str, pd.Series | str]] = {}
    actual = _numeric(df, mapping, "actual_output")
    scrap = _numeric(df, mapping, "scrap_count")
    downtime = _numeric(df, mapping, "downtime_minutes")
    planned = _numeric(df, mapping, "planned_output")
    timestamp = _date(df, mapping, "timestamp")
    machine = _series(df, mapping, "machine_id")
    if actual is not None:
        masks["actual_output < 0"] = {"severity": "critical", "mask": actual < 0}
    if scrap is not None and actual is not None:
        masks["scrap_count > actual_output"] = {"severity": "critical", "mask": scrap > actual}
    if downtime is not None:
        masks["downtime_minutes < 0"] = {"severity": "critical", "mask": downtime < 0}
    if planned is not None:
        masks["planned_output <= 0"] = {"severity": "warning", "mask": planned <= 0}
    if machine is not None:
        masks["missing machine_id"] = {"severity": "critical", "mask": machine.isna() | machine.astype("string").str.strip().eq("")}
    if timestamp is not None:
        masks["missing timestamp"] = {"severity": "critical", "mask": timestamp.isna()}
    return masks


def _logistics_rules(df: pd.DataFrame, mapping: dict[str, str | None]) -> list[QualityRuleResult]:
    template = "Logistics"
    results: list[QualityRuleResult] = []
    order_date = _date(df, mapping, "order_date")
    delivery_date = _date(df, mapping, "delivery_date")
    planned_delivery = _date(df, mapping, "planned_delivery_date")
    if order_date is not None and delivery_date is not None:
        results.append(_result(template, "delivery_date before order_date", "critical", delivery_date < order_date, "Delivery before order date is logically inconsistent.", "Correct order or delivery date values."))
    if delivery_date is not None:
        results.append(_result(template, "missing delivery_date", "critical", delivery_date.isna(), "Missing delivery dates prevent lead-time and on-time calculations.", "Fill delivery dates or separate open shipments from delivered shipments."))
    if planned_delivery is not None:
        results.append(_result(template, "planned_delivery_date missing", "warning", planned_delivery.isna(), "Missing planned delivery dates prevent delay calculations.", "Backfill promised delivery dates where available."))
    shipping_cost = _numeric(df, mapping, "shipping_cost")
    if shipping_cost is not None:
        results.append(_result(template, "shipping_cost < 0", "critical", shipping_cost < 0, "Negative shipping cost may indicate credits or invalid cost capture.", "Validate cost sign conventions before reporting freight cost."))
    carrier = _series(df, mapping, "carrier")
    if carrier is not None:
        results.append(_result(template, "missing carrier", "warning", carrier.isna() | carrier.astype("string").str.strip().eq(""), "Missing carriers weaken carrier performance reporting.", "Backfill carrier names where possible."))
    return results


def _logistics_rule_masks(df: pd.DataFrame, mapping: dict[str, str | None]) -> dict[str, dict[str, pd.Series | str]]:
    masks: dict[str, dict[str, pd.Series | str]] = {}
    order_date = _date(df, mapping, "order_date")
    delivery_date = _date(df, mapping, "delivery_date")
    planned_delivery = _date(df, mapping, "planned_delivery_date")
    if order_date is not None and delivery_date is not None:
        masks["delivery_date before order_date"] = {"severity": "critical", "mask": delivery_date < order_date}
    if delivery_date is not None:
        masks["missing delivery_date"] = {"severity": "critical", "mask": delivery_date.isna()}
    if planned_delivery is not None:
        masks["planned_delivery_date missing"] = {"severity": "warning", "mask": planned_delivery.isna()}
    shipping_cost = _numeric(df, mapping, "shipping_cost")
    if shipping_cost is not None:
        masks["shipping_cost < 0"] = {"severity": "critical", "mask": shipping_cost < 0}
    carrier = _series(df, mapping, "carrier")
    if carrier is not None:
        masks["missing carrier"] = {"severity": "warning", "mask": carrier.isna() | carrier.astype("string").str.strip().eq("")}
    return masks


def _finance_rules(df: pd.DataFrame, mapping: dict[str, str | None]) -> list[QualityRuleResult]:
    template = "Finance"
    results: list[QualityRuleResult] = []
    amount = _numeric(df, mapping, "amount")
    date_values = _date(df, mapping, "date")
    type_values = _series(df, mapping, "type")
    if amount is not None:
        results.append(_result(template, "amount missing or non-numeric", "critical", amount.isna(), "Non-numeric or missing amounts cannot be included in finance KPIs.", "Correct amount formatting and missing values."))
        results.append(_result(template, "amount equals zero", "warning", amount == 0, "Zero-amount rows may be placeholders or corrections.", "Review zero-value transactions before financial reporting."))
    if date_values is not None:
        results.append(_result(template, "date missing", "critical", date_values.isna(), "Rows without valid dates cannot support monthly finance analysis.", "Standardize transaction dates."))
    if type_values is not None:
        normalized = type_values.astype("string").str.strip().str.lower()
        interpretable = normalized.isin(["revenue", "income", "sales", "cost", "expense", "spend", "cogs"])
        results.append(_result(template, "type not interpretable as revenue or cost", "critical", ~interpretable, "Finance KPIs require reliable revenue/cost type values.", "Normalize type values to revenue or cost before KPI reporting."))
    budget = _numeric(df, mapping, "budget")
    budget_raw = _series(df, mapping, "budget")
    actual = _numeric(df, mapping, "actual")
    actual_raw = _series(df, mapping, "actual")
    if budget is not None and actual is not None:
        invalid_budget_actual = (budget.isna() & budget_raw.notna()) | (actual.isna() & actual_raw.notna())
        results.append(_result(template, "budget and actual non-numeric", "warning", invalid_budget_actual, "Non-numeric budget or actual values prevent variance analysis.", "Convert budget and actual fields to numeric values."))
    return results


def _finance_rule_masks(df: pd.DataFrame, mapping: dict[str, str | None]) -> dict[str, dict[str, pd.Series | str]]:
    masks: dict[str, dict[str, pd.Series | str]] = {}
    amount = _numeric(df, mapping, "amount")
    date_values = _date(df, mapping, "date")
    type_values = _series(df, mapping, "type")
    if amount is not None:
        masks["amount missing or non-numeric"] = {"severity": "critical", "mask": amount.isna()}
        masks["amount equals zero"] = {"severity": "warning", "mask": amount == 0}
    if date_values is not None:
        masks["date missing"] = {"severity": "critical", "mask": date_values.isna()}
    if type_values is not None:
        normalized = type_values.astype("string").str.strip().str.lower()
        interpretable = normalized.isin(["revenue", "income", "sales", "cost", "expense", "spend", "cogs"])
        masks["type not interpretable as revenue or cost"] = {"severity": "critical", "mask": ~interpretable}
    budget = _numeric(df, mapping, "budget")
    budget_raw = _series(df, mapping, "budget")
    actual = _numeric(df, mapping, "actual")
    actual_raw = _series(df, mapping, "actual")
    if budget is not None and actual is not None:
        masks["budget and actual non-numeric"] = {"severity": "warning", "mask": (budget.isna() & budget_raw.notna()) | (actual.isna() & actual_raw.notna())}
    return masks
