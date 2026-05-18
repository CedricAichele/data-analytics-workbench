SELECT
    product_name,
    product_category,
    ROUND(SUM(net_revenue), 2) AS net_revenue,
    ROUND(SUM(quantity), 2) AS quantity_sold,
    COUNT(DISTINCT order_id) AS order_count
FROM cleaned_orders
WHERE is_analysis_valid
GROUP BY product_name, product_category
ORDER BY net_revenue DESC, product_name
LIMIT 100;

