-- Umsatz pro Stadt
SELECT c.city,
       ROUND(SUM(o.quantity * p.unit_price), 2) AS revenue,
       COUNT(DISTINCT c.customer_id)            AS customers
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products  p ON o.product_id  = p.product_id
GROUP BY c.city
ORDER BY revenue DESC;