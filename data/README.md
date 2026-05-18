# Data

This folder contains small synthetic sample datasets used by Data Analytics Workbench.

## Sample Retail Orders

`sample/sample_retail_orders.csv` is a synthetic retail order dataset with more than 500 rows. It is designed to be realistic enough for portfolio demonstrations while remaining small enough for GitHub.

The sample includes intentional data quality issues:

- missing customer IDs
- duplicated rows
- negative quantities for returns
- zero or invalid unit prices
- mixed date formats
- cancelled orders

The data is synthetic and does not represent real customers or transactions.

## Sample Manufacturing Operations

`sample/sample_manufacturing_operations.csv` is a synthetic production operations dataset with more than 500 rows.

The sample includes:

- production timestamps
- machine IDs
- production lines
- shifts
- products
- planned output
- actual output
- scrap count
- downtime minutes
- runtime minutes
- quality status

It includes intentional data quality issues:

- missing machine IDs
- duplicated rows
- zero planned output
- missing shift values
- occasional high scrap counts
- occasional high downtime

The data is synthetic and does not represent a real factory, production line, customer, or product.
