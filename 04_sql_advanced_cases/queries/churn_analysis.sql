-- Kunden ohne jede Bestellung (potenzielle Churn-Kandidaten)
WITH customer_orders AS (
    SELECT c.customer_id, c.customer_name, c.city, COUNT(o.order_id) AS order_count
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.customer_name, c.city
)
SELECT customer_name, city, order_count
FROM customer_orders
WHERE order_count = 0
ORDER BY customer_name;
