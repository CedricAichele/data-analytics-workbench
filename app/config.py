"""Application configuration and shared constants."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
SAMPLE_RETAIL_PATH = SAMPLE_DATA_DIR / "sample_retail_orders.csv"
SQL_DIR = PROJECT_ROOT / "sql"
LOGO_PATH = ASSETS_DIR / "logo.svg"

APP_TITLE = "Data Analytics Workbench"
APP_SUBTITLE = "Profiling, Preparation, Data Quality & KPI Analytics"
APP_DESCRIPTION = (
    "Upload raw datasets, inspect data quality, apply controlled transformations, "
    "map business fields and generate transparent KPI analytics."
)

RETAIL_TEMPLATE_NAME = "Retail / Sales Analytics"

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

OPERATIONS_TEMPLATE_PLACEHOLDER = {
    "name": "Operations / Manufacturing Analytics",
    "status": "planned",
    "description": "Architecture placeholder for future production throughput, downtime, and defect analytics.",
}
