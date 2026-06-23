-- Kunden mit Gesamtumsatz ueber 500 EUR
SELECT c.customer_name,
       ROUND(SUM(o.quantity * p.unit_price), 2) AS revenue
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products  p ON o.product_id  = p.product_id
GROUP BY c.customer_id, c.customer_name
HAVING revenue > 500
ORDER BY revenue DESC;