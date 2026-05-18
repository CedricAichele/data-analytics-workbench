"""Application configuration and shared constants."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
SAMPLE_RETAIL_PATH = SAMPLE_DATA_DIR / "sample_retail_orders.csv"
SAMPLE_MANUFACTURING_PATH = SAMPLE_DATA_DIR / "sample_manufacturing_operations.csv"
SQL_DIR = PROJECT_ROOT / "sql"
LOGO_PATH = ASSETS_DIR / "logo.svg"
LOGO_MARK_PATH = ASSETS_DIR / "logo_mark.svg"
ICONS_DIR = ASSETS_DIR / "icons"

APP_TITLE = "Data Analytics Workbench"
APP_SUBTITLE = "Profiling, Preparation, Data Quality & KPI Analytics"
APP_DESCRIPTION = (
    "Upload raw datasets, inspect data quality, apply controlled transformations, "
    "map business fields and generate transparent KPI analytics."
)

RETAIL_TEMPLATE_NAME = "Retail / Sales Analytics"
MANUFACTURING_TEMPLATE_NAME = "Manufacturing Analytics"

RETAIL_REQUIRED_FIELDS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_name",
    "quantity",
    "unit_price",
]

RETAIL_OPTIONAL_FIELDS = [
    "country",
    "product_category",
    "invoice_status",
]

ALL_RETAIL_FIELDS = RETAIL_REQUIRED_FIELDS + RETAIL_OPTIONAL_FIELDS

MANUFACTURING_REQUIRED_FIELDS = [
    "timestamp",
    "machine_id",
    "actual_output",
    "scrap_count",
    "downtime_minutes",
]

MANUFACTURING_OPTIONAL_FIELDS = [
    "planned_output",
    "runtime_minutes",
    "line",
    "shift",
    "product",
    "quality_status",
]

ALL_MANUFACTURING_FIELDS = MANUFACTURING_REQUIRED_FIELDS + MANUFACTURING_OPTIONAL_FIELDS
