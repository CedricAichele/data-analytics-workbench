# App Walkthrough

This walkthrough documents the current Data Analytics Workbench UI and workflow. Automated localhost screenshots were blocked in this environment, but the Streamlit smoke check confirms the app responds at:

```text
http://127.0.0.1:8501
```

## Global Layout

The app uses Streamlit wide layout with a light professional theme. The sidebar shows a larger workbench-themed analytics logo and a custom navigation menu with professional icon labels.

Navigation items:

- Overview
- Data Upload
- Data Profile
- Data Preparation
- Data Quality
- Generic Analytics
- Template Selection
- Column Mapping
- Sales Analytics
- Manufacturing Analytics
- Logistics Analytics
- Finance Analytics
- Management Summary

## Overview

The Overview page explains the two-layer architecture:

- Generic workflow for any supported tabular dataset
- Domain templates that require schema detection or manual mapping

It also explains that `raw_df` remains unchanged, `working_df` is the transformed copy, extra columns are preserved, and analytics pages do not permanently mutate data.

Before data is loaded, the page shows that no dataset is loaded. After loading data, it shows raw and working row/column counts.

## Data Upload

The Data Upload page accepts:

- CSV
- Excel `.xlsx`
- JSON `.json`

Excel workbooks with multiple sheets show a sheet selector. JSON supports tabular records, JSON Lines, records-style objects, and simple nested records.

The page also includes two sample buttons:

- Load sample retail dataset
- Load sample manufacturing dataset

After loading any dataset, the app stores `raw_df`, copies it to `working_df`, records `dataset_metadata`, clears stale mappings and analytics, and runs initial template detection for Sales / Retail and Manufacturing.

## Data Profile

The Data Profile page works with any `working_df`.

It shows:

- row and column counts
- duplicate row count
- generic quality score
- data types and missing values
- unique values
- numeric summary
- categorical summary
- detected date-like, numeric, and categorical columns
- missing value chart
- data type distribution chart
- selected numeric distribution
- selected categorical frequency chart

If no dataset is loaded, the page shows a clear warning and stops safely.

## Data Preparation

The Data Preparation page is the only place for user-triggered permanent data transformations.

It modifies `working_df` only and logs each successful transformation.

Available actions:

- rename column
- drop columns
- change column type
- parse datetime column
- fill missing values
- drop rows with missing values
- remove duplicate rows
- filter rows
- create revenue column
- reset `working_df` to `raw_df`
- download `working_df` as CSV

When a transformation changes structure, stale mappings and analytics outputs are cleared.

## Data Quality

The Data Quality page shows:

- generic quality score for any dataset
- missing value, duplicate, and invalid numeric sub-scores
- explanations and recommended fixes
- optional template-aware quality score when a valid mapping exists

Template-aware scoring checks schema completeness, mapped date parsing, and mapped numeric fields.

## Generic Analytics

The Generic Analytics page works with arbitrary supported datasets.

Users select:

- numeric measure
- optional category
- optional date column
- aggregation
- chart type

The page returns:

- aggregated table
- Plotly chart
- basic insights
- missing value counts for selected fields
- rows used
- CSV download of the aggregated result

It does not assume sales, manufacturing, finance, or logistics meaning.

## Template Selection

Template Selection shows cards for:

- Generic Analytics
- Sales / Retail Analytics
- Manufacturing Analytics
- Logistics Analytics
- Finance Analytics

Each card shows purpose, status, required fields, optional fields, mapping requirement, sample dataset availability, and notes.

Sales / Retail and Manufacturing are implemented. Logistics and Finance are visible planned templates.

## Column Mapping

Column Mapping supports implemented domain templates:

- Sales / Retail
- Manufacturing

The page shows schema detection confidence, matched fields, missing required fields, and selectboxes for required and optional field mapping. Mappings are validated before saving.

Sales / Retail mapping is kept compatible with the existing `column_mapping` state key. Manufacturing mapping is stored separately and also in `template_mappings`.

## Sales Analytics

Sales Analytics requires a valid Sales / Retail mapping.

It shows:

- gross sales revenue
- net revenue
- valid orders
- valid customers
- average order value
- quantity sold
- return rate
- cancelled order rate
- top 10 customer revenue share
- revenue and order charts
- product, customer, country, RFM, issue, and cleaned preview tables

It uses mapped fields for KPI logic and preserves extra dataset columns outside the temporary analytical layer.

## Manufacturing Analytics

Manufacturing Analytics requires a valid Manufacturing mapping.

It shows:

- total output
- total scrap
- scrap rate
- downtime minutes
- average downtime per machine
- production attainment when planned output is available
- availability approximation when runtime and downtime are available
- quality rate approximation
- simplified OEE approximation when defensible
- output and downtime trends
- machine performance charts and tables
- output by line and shift when available
- issue summary

The simplified OEE metric is labeled as an approximation, not a certified OEE standard.

## Logistics Analytics

Logistics Analytics is a planned template page. It documents the intended schema and directs users to Generic Analytics for logistics datasets today.

## Finance Analytics

Finance Analytics is a planned template page. It documents the intended schema and warns that finance interpretation requires an explicit type, category, or sign convention.

## Management Summary

Management Summary generates deterministic text from calculated Sales / Retail analytics. It includes an LLM extension placeholder but does not call external APIs or require API keys.
