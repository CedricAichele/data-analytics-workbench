SELECT
    CAST(date_trunc('month', order_date) AS DATE) AS month,
    ROUND(SUM(gross_revenue), 2) AS gross_revenue,
    ROUND(SUM(net_revenue), 2) AS net_revenue,
    COUNT(DISTINCT CASE WHEN is_analysis_valid THEN order_id END) AS order_count,
    SUM(CASE WHEN is_return AND NOT is_duplicate_row THEN 1 ELSE 0 END) AS return_rows,
    COUNT(DISTINCT CASE WHEN is_cancelled AND NOT is_duplicate_row THEN order_id END) AS cancelled_orders
FROM cleaned_orders
WHERE order_date IS NOT NULL
GROUP BY 1
ORDER BY 1;
