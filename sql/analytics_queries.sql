-- ============================================================================
-- Bharat Connect Analytics Hub — Analytics SQL library
-- Works on SQLite and PostgreSQL (minor dialect notes inline).
--
-- Suggested star-schema modelling for Power BI / Metabase:
--   fact_sales            (grain: one row per order item)
--     ├─ dim_customer    (customer_id, state, is_rural, age_band)
--     ├─ dim_seller      (seller_id, seller_name, rating)
--     ├─ dim_product     (product_id, category, unit_price, cost_price)
--     ├─ dim_date        (date, year, quarter, month, month_name)
--     └─ dim_payment     (method)
-- ============================================================================

-- 1. Monthly GMV and order count (rural vs urban)
SELECT strftime('%Y-%m', o.order_date) AS year_month,
       SUM(oi.line_total)              AS gmv,
       COUNT(DISTINCT o.order_id)      AS orders,
       SUM(CASE WHEN c.is_rural THEN oi.line_total ELSE 0 END) AS rural_gmv,
       SUM(CASE WHEN NOT c.is_rural THEN oi.line_total ELSE 0 END) AS urban_gmv
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers   c  ON c.customer_id = o.customer_id
WHERE o.status = 'delivered'
GROUP BY 1 ORDER BY 1;

-- 2. Average order value by month
SELECT strftime('%Y-%m', o.order_date) AS year_month,
       ROUND(SUM(oi.line_total) * 1.0 / COUNT(DISTINCT o.order_id), 2) AS aov
FROM orders o JOIN order_items oi USING(order_id)
WHERE o.status = 'delivered'
GROUP BY 1 ORDER BY 1;

-- 3. Top 10 sellers by revenue
SELECT s.seller_id, s.seller_name, s.state, s.rating,
       ROUND(SUM(oi.line_total), 2) AS revenue,
       COUNT(DISTINCT oi.order_id) AS orders
FROM order_items oi
JOIN sellers s USING(seller_id)
JOIN orders  o USING(order_id)
WHERE o.status = 'delivered'
GROUP BY 1,2,3,4
ORDER BY revenue DESC
LIMIT 10;

-- 4. Category-wise revenue and margin
SELECT p.category,
       ROUND(SUM(oi.line_total), 2)                       AS revenue,
       ROUND(SUM(oi.line_total - p.cost_price*oi.quantity), 2) AS margin,
       ROUND(SUM(oi.line_total - p.cost_price*oi.quantity) * 100.0
             / SUM(oi.line_total), 2)                     AS margin_pct
FROM order_items oi
JOIN products p USING(product_id)
JOIN orders   o USING(order_id)
WHERE o.status = 'delivered'
GROUP BY 1 ORDER BY revenue DESC;

-- 5. State-wise revenue and rural share
SELECT c.state,
       ROUND(SUM(oi.line_total), 2) AS revenue,
       ROUND(SUM(CASE WHEN c.is_rural THEN oi.line_total ELSE 0 END) * 100.0
             / SUM(oi.line_total), 2) AS rural_pct
FROM order_items oi JOIN orders o USING(order_id) JOIN customers c USING(customer_id)
WHERE o.status = 'delivered'
GROUP BY 1 ORDER BY revenue DESC;

-- 6. Cohort retention (signup month vs months active)
-- Postgres: replace strftime() with to_char(... , 'YYYY-MM')
WITH first_order AS (
    SELECT customer_id, MIN(strftime('%Y-%m', order_date)) AS cohort
    FROM orders WHERE status='delivered' GROUP BY 1
), activity AS (
    SELECT o.customer_id, fo.cohort,
           strftime('%Y-%m', o.order_date) AS active_month
    FROM orders o JOIN first_order fo USING(customer_id)
    WHERE o.status='delivered'
)
SELECT cohort, active_month,
       COUNT(DISTINCT customer_id) AS active_customers
FROM activity GROUP BY 1,2 ORDER BY 1,2;

-- 7. Repeat purchase rate
SELECT ROUND(SUM(CASE WHEN orders_count > 1 THEN 1 ELSE 0 END) * 100.0
             / COUNT(*), 2) AS repeat_rate_pct
FROM (
  SELECT customer_id, COUNT(DISTINCT order_id) AS orders_count
  FROM orders WHERE status='delivered' GROUP BY 1
) t;

-- 8. Payment-method mix
SELECT method,
       COUNT(*) AS txns,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct,
       ROUND(SUM(amount), 2) AS volume
FROM payments GROUP BY 1 ORDER BY share_pct DESC;

-- 9. Delivery efficiency — rural vs urban
SELECT CASE WHEN c.is_rural THEN 'Rural' ELSE 'Urban' END AS segment,
       ROUND(AVG(d.delivery_days), 2) AS avg_delivery_days,
       ROUND(SUM(CASE WHEN d.on_time THEN 1 ELSE 0 END) * 100.0
             / COUNT(*), 2) AS on_time_pct
FROM deliveries d
JOIN orders    o USING(order_id)
JOIN customers c USING(customer_id)
GROUP BY 1;

-- 10. RFM segmentation (recency days, frequency, monetary)
WITH base AS (
  SELECT o.customer_id,
         julianday('now') - julianday(MAX(o.order_date))     AS recency,
         COUNT(DISTINCT o.order_id)                          AS frequency,
         ROUND(SUM(oi.line_total), 2)                        AS monetary
  FROM orders o JOIN order_items oi USING(order_id)
  WHERE o.status='delivered'
  GROUP BY 1
)
SELECT customer_id, recency, frequency, monetary,
       NTILE(5) OVER (ORDER BY recency DESC)    AS r_score,
       NTILE(5) OVER (ORDER BY frequency)       AS f_score,
       NTILE(5) OVER (ORDER BY monetary)        AS m_score
FROM base;

-- 11. Top growing categories (last 3 months vs previous 3)
WITH m AS (
  SELECT p.category, strftime('%Y-%m', o.order_date) AS ym, SUM(oi.line_total) AS rev
  FROM order_items oi JOIN products p USING(product_id) JOIN orders o USING(order_id)
  WHERE o.status='delivered' GROUP BY 1,2
), ranked AS (
  SELECT category, ym, rev,
         DENSE_RANK() OVER (ORDER BY ym DESC) AS rk
  FROM m
)
SELECT category,
       SUM(CASE WHEN rk <= 3 THEN rev ELSE 0 END) AS last_3m,
       SUM(CASE WHEN rk BETWEEN 4 AND 6 THEN rev ELSE 0 END) AS prev_3m,
       ROUND((SUM(CASE WHEN rk <= 3 THEN rev ELSE 0 END)
              - SUM(CASE WHEN rk BETWEEN 4 AND 6 THEN rev ELSE 0 END)) * 100.0
              / NULLIF(SUM(CASE WHEN rk BETWEEN 4 AND 6 THEN rev ELSE 0 END), 0), 2) AS growth_pct
FROM ranked GROUP BY 1 ORDER BY growth_pct DESC;

-- 12. Top 20 customers by lifetime value
SELECT c.customer_id, c.name, c.state, c.is_rural,
       ROUND(SUM(oi.line_total), 2) AS ltv,
       COUNT(DISTINCT o.order_id)   AS orders
FROM customers c JOIN orders o USING(customer_id) JOIN order_items oi USING(order_id)
WHERE o.status='delivered'
GROUP BY 1,2,3,4 ORDER BY ltv DESC LIMIT 20;

-- 13. Cancellation & return rate by category
SELECT p.category,
       ROUND(SUM(CASE WHEN o.status='cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS cancel_pct,
       ROUND(SUM(CASE WHEN o.status='returned'  THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS return_pct
FROM orders o JOIN order_items oi USING(order_id) JOIN products p USING(product_id)
GROUP BY 1 ORDER BY return_pct DESC;

-- 14. Seller scorecard
SELECT s.seller_id, s.seller_name, s.rating,
       ROUND(SUM(oi.line_total), 2) AS revenue,
       ROUND(AVG(d.delivery_days), 2) AS avg_delivery,
       ROUND(SUM(CASE WHEN d.on_time THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct
FROM sellers s
JOIN order_items oi USING(seller_id)
JOIN orders     o   USING(order_id)
JOIN deliveries d   USING(order_id)
WHERE o.status='delivered'
GROUP BY 1,2,3 ORDER BY revenue DESC;

-- 15. New vs returning customer revenue per month
WITH first_dt AS (
  SELECT customer_id, MIN(date(order_date)) AS first_order_date
  FROM orders WHERE status='delivered' GROUP BY 1
)
SELECT strftime('%Y-%m', o.order_date) AS ym,
       SUM(CASE WHEN date(o.order_date) = f.first_order_date THEN oi.line_total ELSE 0 END) AS new_cust_rev,
       SUM(CASE WHEN date(o.order_date) > f.first_order_date THEN oi.line_total ELSE 0 END) AS returning_rev
FROM orders o JOIN first_dt f USING(customer_id) JOIN order_items oi USING(order_id)
WHERE o.status='delivered'
GROUP BY 1 ORDER BY 1;
