WITH reference_date AS (
    SELECT MAX(order_date) + INTERVAL 1 DAY AS as_of_date
    FROM cleaned_orders
    WHERE is_analysis_valid
),
customer_base AS (
    SELECT
        customer_id,
        DATE_DIFF('day', MAX(order_date), MAX(reference_date.as_of_date)) AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        ROUND(SUM(net_revenue), 2) AS monetary
    FROM cleaned_orders
    CROSS JOIN reference_date
    WHERE
        is_analysis_valid
        AND customer_id IS NOT NULL
        AND TRIM(CAST(customer_id AS VARCHAR)) <> ''
    GROUP BY customer_id
)
SELECT *
FROM customer_base
WHERE monetary > 0
ORDER BY monetary DESC;

