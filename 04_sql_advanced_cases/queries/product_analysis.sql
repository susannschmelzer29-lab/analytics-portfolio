-- Produktumsatz mit Rang (Window Function)
SELECT p.product_name,
       p.category,
       SUM(o.quantity)                          AS units_sold,
       ROUND(SUM(o.quantity * p.unit_price), 2) AS revenue,
       RANK() OVER (ORDER BY SUM(o.quantity * p.unit_price) DESC) AS revenue_rank
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue_rank;