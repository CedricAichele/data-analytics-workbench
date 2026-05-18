# Feature Report

This report lists only features that are implemented in the current Data Analytics Workbench codebase.

## Implemented Pages

- Landing page: app overview, workflow, template architecture, readiness status.
- Data Upload: CSV, XLSX, JSON upload plus bundled sample retail dataset.
- Data Profile: generic dataframe profiling and generic quality score.
- Data Preparation: controlled transformations on `working_df`.
- Column Mapping: retail schema detection and manual mapping.
- Retail Analytics: retail KPIs, charts, quality score, RFM segmentation, and detail tables.
- Management Summary: deterministic text summary from retail analytics.

There is no standalone Data Quality page. Data quality appears in Data Profile and Retail Analytics.

## Supported File Formats

- CSV `.csv`
- Excel `.xlsx`
- JSON `.json`

CSV and Excel are the primary supported formats. JSON is best effort for tabular records, JSON Lines, records-oriented JSON, and simple nested records that can be normalized.

## Upload Behavior

Uploaded files are loaded through `app/services/data_loader.py`.

- File extensions are inspected before dispatching to the correct loader.
- CSV uses UTF-8 first and latin1 fallback.
- Excel uses `openpyxl`; multi-sheet workbooks can be loaded by selected sheet.
- JSON uses Python JSON parsing, JSON Lines fallback, and `pandas.json_normalize` for simple nested records.
- Unsupported extensions and invalid content raise clear `ValueError` messages.
- Loaded datasets are validated to ensure they produce a non-empty pandas DataFrame.

On successful upload, the app sets:

- `raw_df`
- `working_df`
- `dataset_metadata`
- `transformation_log`

It clears stale column mapping and retail analytics results.

## Sample Dataset Behavior

The bundled sample dataset is `data/sample/sample_retail_orders.csv`.

When loaded, it is stored as `raw_df`, copied to `working_df`, and tagged in metadata with `source = sample`. Previous transformations, mappings, and analytics results are cleared.

The sample dataset is synthetic and includes realistic quality issues:

- missing customer IDs
- duplicate rows
- negative quantities for returns
- zero or invalid unit prices
- mixed date formats
- cancelled orders

## Data Profiling Features

The generic profiler works on the current `working_df` and is independent of the retail template.

Implemented profiling outputs:

- row count
- column count
- column names
- detected data types
- missing values per column
- missing value percentage per column
- duplicate row count
- unique values per column
- numeric summary
- categorical summary
- detected date-like columns
- detected numeric columns
- detected categorical columns
- missing values chart
- data type distribution chart
- selected numeric column distribution chart
- selected categorical frequency chart

## Data Preparation Transformations

The Data Preparation page applies transformations only to `working_df`.

Implemented transformations:

- rename column
- drop columns
- change column type
- parse datetime column
- remove duplicate rows
- fill missing values with numeric zero
- fill missing numeric values with median
- fill text missing values with `Unknown`
- drop rows with missing values in a selected column
- filter rows with supported operators
- create revenue column from quantity and unit price
- reset `working_df` to `raw_df`

Supported type targets:

- string
- integer
- float
- datetime
- boolean

Supported row filters:

- equals
- not equals
- contains
- greater than
- greater than or equal
- less than
- less than or equal

## Transformation Log Behavior

Each successful transformation appends a human-readable entry to `transformation_log`.

The log is displayed in order on the Data Preparation page. Resetting the working dataset clears the log. Loading a new upload or sample dataset also clears the log.

## Data Quality Score Behavior

The quality score is deterministic and explainable. It returns:

- overall score
- sub-scores
- explanations
- recommended fixes

Implemented dimensions include:

- missing values
- duplicate rows
- invalid numeric values
- schema completeness when mapping and required fields are supplied
- date parsing issues when date fields are supplied

Generic quality scoring appears on the Data Profile page. Template-aware quality scoring appears on the Retail Analytics page.

## Schema Detection Behavior

The retail schema detector is rule-based. It checks uploaded column names against retail field synonyms and fuzzy matches.

It reports:

- detected template
- confidence score
- matched fields
- missing required fields
- whether manual mapping is required

Retail fields include order ID, order date, customer ID, product name, quantity, unit price, country, product category, and invoice status.

## Column Mapping Behavior

The Column Mapping page lets users manually map the current `working_df` columns to the retail analytics schema.

Required retail fields:

- `order_id`
- `order_date`
- `customer_id`
- `product_name`
- `quantity`
- `unit_price`

Optional retail fields:

- `country`
- `product_category`
- `invoice_status`

Mappings are pre-filled from schema detection where possible. The app validates that required fields are mapped to real columns before enabling the save action.

## Retail KPI Features

Retail analytics are available only after a valid mapping is saved.

Implemented KPIs:

- gross sales revenue
- net revenue
- valid orders
- valid customers
- average order value
- quantity sold
- return rate
- cancelled order rate
- revenue share from top 10 customers

Implemented charts and tables:

- revenue by month
- order count by month
- returns by month
- revenue by product category when available
- top products by revenue
- top customers by revenue
- revenue by country when available
- top products table
- customer RFM table
- country performance table
- data quality issue table
- cleaned orders preview

## Retail Cleaning Behavior

The retail cleaning pipeline:

- standardizes mapped columns internally
- parses order dates
- calculates gross and net revenue fields
- flags returns where quantity is negative
- flags invalid prices where unit price is less than or equal to zero
- flags missing customer IDs
- flags cancelled orders using invoice status when available
- flags duplicate rows
- keeps an issue summary for review

Problem rows are flagged and summarized rather than silently removed from visibility.

## RFM Features

RFM analysis is implemented for valid retail rows.

It calculates:

- recency
- frequency
- monetary value
- RFM scores from 1 to 5
- customer segment

Implemented segments:

- Champions
- Loyal Customers
- Potential Loyalists
- New Customers
- At Risk
- Low Value

The app shows segment counts, segment revenue, a segment distribution chart, and the customer RFM table.

## DuckDB and SQL Usage

DuckDB is used for analytical aggregations after retail cleaning.

SQL files are stored in `sql/`:

- `retail_cleaned_orders.sql`
- `retail_monthly_revenue.sql`
- `retail_product_performance.sql`
- `retail_country_performance.sql`
- `retail_customer_rfm.sql`

The SQL service loads queries from the repository-relative `sql/` directory and executes them against an in-memory DuckDB connection.

## Management Summary Behavior

The Management Summary page generates deterministic narrative text from calculated retail metrics. It does not call OpenAI, Claude, or any external LLM.

The page includes a disabled LLM extension placeholder for future work.

## Export Features

The Data Preparation page supports downloading the current `working_df` as CSV.

Excel and JSON export are not implemented.

## Known Limitations

- The app stores data in Streamlit session state and does not persist uploads to a database.
- JSON upload is limited to tabular or normalizable structures.
- `.xls` Excel files are not supported.
- Schema detection is rule-based and may require manual correction.
- Retail analytics require a valid mapping before KPI calculation.
- The Operations / Manufacturing template is a placeholder only.
- There is no authentication, backend API, or production database.
- Screenshots were not captured automatically in this environment because local browser access was blocked.

## Not-Yet-Implemented Ideas

- Operations / Manufacturing analytics template.
- Saved mapping profiles.
- Richer regional date parsing controls.
- Optional Excel export of prepared data.
- Deployed app screenshots for the README.
- More robust JSON schema exploration for complex API payloads.

