# App Walkthrough

This walkthrough is the final visual review package for Data Analytics Workbench. A live Streamlit preview was started successfully at:

```text
http://127.0.0.1:8501
```

Automated browser screenshots could not be captured in this environment because the in-app browser blocked local Streamlit URLs with `net::ERR_BLOCKED_BY_CLIENT`. The app itself responded successfully over HTTP, so the sections below document the visible UI and expected page states.

## Global Layout

The app uses Streamlit wide layout with a clean light theme from `.streamlit/config.toml`. The sidebar shows the Data Analytics Workbench logo when `assets/logo.svg` is available, then the app title and subtitle.

The app title is:

```text
Data Analytics Workbench
```

The subtitle is:

```text
Profiling, Preparation, Data Quality & KPI Analytics
```

The app description explains that users can upload raw datasets, inspect data quality, apply controlled transformations, map business fields, and generate transparent KPI analytics.

## Landing Page

Before a dataset is loaded, the landing page shows:

- the app title and subtitle
- the short app description
- an info message that no dataset is loaded yet
- a six-step workflow:
  - Data Upload
  - Data Profile
  - Data Preparation
  - Column Mapping
  - Retail Analytics
  - Summary
- a Template Architecture table showing Retail / Sales Analytics as implemented and Operations / Manufacturing Analytics as planned
- a Readiness panel with disabled checkboxes for dataset loaded, working copy ready, retail mapping saved, and retail analytics calculated

After a dataset is loaded, the landing page status changes to show the dataset name plus raw and working row/column counts.

## Data Upload Page

Before a dataset is loaded, the page shows:

- page title: `Data Upload`
- accepted formats caption: `CSV, Excel .xlsx, JSON .json`
- file uploader accepting `.csv`, `.xlsx`, and `.json`
- a `Load uploaded dataset` button after a file is selected
- a bundled sample section with `Load sample retail dataset`

For Excel `.xlsx` uploads:

- if the workbook has multiple sheets, the page displays an Excel sheet selectbox
- if the workbook has one sheet, the page displays the selected sheet name as a caption

After loading an uploaded CSV, XLSX, or JSON file, the page stores:

- `raw_df`
- `working_df`
- `dataset_metadata`
- `transformation_log`

It also clears saved retail mapping and prior retail analytics results. The page then shows:

- loaded file name
- detected file type
- row count
- column count
- source
- sheet name for Excel files when available
- working data preview
- initial retail schema detection with confidence, matched fields, and missing required fields

After loading the bundled sample dataset, the page shows the same metadata and preview, with `source` set to `sample`.

## Data Profile Page

Before a dataset is loaded, the page shows a clear warning telling the user to load a CSV, XLSX, JSON, or bundled sample dataset first, then stops cleanly.

After a dataset is loaded, the page profiles `working_df`. It shows:

- KPI cards for rows, columns, duplicate rows, and generic quality score
- generic data quality score progress bar
- sub-score table
- expandable explanations and recommended fixes
- column overview tabs:
  - Types and Missingness
  - Unique Values
  - Numeric Summary
  - Categorical Summary
  - Detected Column Groups
- visual profiling charts:
  - missing values bar chart
  - data type distribution chart
  - selected numeric column distribution
  - selected categorical column frequency

The generic profiler is domain-neutral and does not require retail columns.

## Data Quality View

There is no standalone Data Quality page. Data quality is implemented in two places:

- the Data Profile page shows a generic dataset-level quality score
- the Retail Analytics page shows a template-aware quality score that includes schema, date, and numeric validation using the saved retail mapping

Both views show sub-scores, plain-language explanations, and recommended fixes.

## Data Preparation Page

Before a dataset is loaded, the page shows the same missing-dataset warning and stops cleanly.

After a dataset is loaded, the page operates only on `working_df`. It does not mutate `raw_df`.

Visible sections include:

- Dataset Status:
  - raw data loaded status
  - working row count
  - working column count
  - transformation count
  - last transformation, when available
- Preview Working Data:
  - first rows of the current `working_df`
- Column Operations:
  - rename a selected column
  - drop selected columns
- Type Conversion:
  - select column
  - select target type: string, integer, float, datetime, boolean
  - apply conversion with warning when missing values increase
- Date Parsing:
  - select a column
  - parse as datetime
  - show failed parse count
- Missing Values:
  - select a column
  - choose strategy
  - fill numeric missing with zero
  - fill numeric missing with median
  - fill text missing with Unknown
  - drop rows with missing values
- Duplicates:
  - duplicate row count
  - remove duplicate rows button
- Row Filtering:
  - select column
  - choose operator
  - enter comparison value
  - apply filter
- Calculated Column:
  - choose quantity column
  - choose unit price column
  - create revenue column
- Transformation Log:
  - ordered list of applied transformations
- Reset and Export:
  - reset working data to original upload
  - download `working_df` as CSV

Every successful transformation appends a human-readable entry to `transformation_log`.

## Column Mapping Page

Before a dataset is loaded, the page shows the missing-dataset warning and stops cleanly.

After a dataset is loaded, the page shows:

- schema detection metrics:
  - detected template
  - confidence score
  - whether manual mapping is required
- expandable matched and missing fields
- required retail field selectboxes:
  - `order_id`
  - `order_date`
  - `customer_id`
  - `product_name`
  - `quantity`
  - `unit_price`
- optional retail field selectboxes:
  - `country`
  - `product_category`
  - `invoice_status`
- validation warnings or success message
- disabled/enabled `Save retail mapping` button based on mapping validity
- expandable current mapping JSON

The page pre-fills mappings using schema detection when possible.

## Retail Analytics Page

Before a dataset is loaded, the page shows the missing-dataset warning and stops cleanly.

If a dataset is loaded but no valid retail mapping is saved, the page warns the user to save a valid retail mapping first and stops cleanly.

After a valid retail mapping is saved, the page shows:

- Retail KPI cards:
  - gross sales revenue
  - net revenue
  - valid orders
  - valid customers
  - average order value
  - quantity sold
  - return rate
  - cancelled rate
  - revenue from top 10 customers
- expandable KPI definitions
- template quality score and sub-scores
- expandable quality explanations and recommended fixes
- revenue and order charts:
  - revenue by month
  - order count by month
  - returns by month
  - revenue by product category when available
- product and customer performance charts:
  - top products by revenue
  - top customers by revenue
- country performance chart when country data is available
- RFM Customer Segmentation:
  - segment distribution chart
  - segment summary table
- detail tabs:
  - Top Products
  - Customer RFM
  - Country Performance
  - Data Quality Issues
  - Cleaned Orders Preview

The retail analytics page uses DuckDB-backed SQL queries for analytical aggregations after the retail cleaning step.

## Management Summary Page

Before a dataset is loaded, the page shows the missing-dataset warning and stops cleanly.

If retail analytics have not been calculated and no valid retail mapping exists, the page warns the user to run Retail Analytics first or save a valid retail mapping.

After retail analytics are available, the page shows:

- a deterministic text summary generated from calculated metrics
- an expandable placeholder for a future LLM summary extension
- supporting metrics table

The MVP does not call external LLM APIs and does not require API keys.

## Upload Behavior by Format

### CSV

CSV uploads are read with UTF-8 first and latin1 fallback. Empty or non-tabular CSV files produce a clear error.

### Excel XLSX

Excel uploads use `openpyxl`. Multi-sheet workbooks show a sheet selector before loading. `.xls` files are rejected with a message asking the user to save as `.xlsx`.

### JSON

JSON uploads support:

- arrays of records
- records-oriented JSON objects
- JSON Lines
- simple nested records that can be flattened with `pandas.json_normalize`

Deeply nested or scalar JSON is rejected with a clear error explaining that the JSON must represent tabular records.

## Sample Dataset Flow

Loading the bundled sample dataset:

- loads `data/sample/sample_retail_orders.csv`
- stores the original data in `raw_df`
- stores a copy in `working_df`
- sets `dataset_metadata` with `source = sample`
- clears previous transformation log
- clears previous column mapping and retail analytics results
- runs initial retail schema detection

The sample dataset includes intentional quality issues such as missing customer IDs, duplicate rows, returns, invalid prices, mixed date formats, and cancelled orders.

