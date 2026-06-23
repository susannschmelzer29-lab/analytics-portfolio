-- Gesamtumsatz ueber alle Bestellungen (quantity * unit_price)
SELECT ROUND(SUM(o.quantity * p.unit_price), 2) AS total_revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id;