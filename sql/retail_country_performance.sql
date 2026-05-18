SELECT
    country,
    ROUND(SUM(net_revenue), 2) AS net_revenue,
    COUNT(DISTINCT order_id) AS order_count,
    COUNT(DISTINCT customer_id) AS customer_count
FROM cleaned_orders
WHERE is_analysis_valid
GROUP BY country
ORDER BY net_revenue DESC, country;

