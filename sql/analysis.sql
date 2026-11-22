-- Q1. Overall summary
SELECT COUNT(*) AS rows_,
       COUNT(DISTINCT invoice_no) AS orders,
       COUNT(DISTINCT customer_id) AS customers,
       ROUND(SUM(revenue), 0) AS total_revenue,
       ROUND(SUM(revenue) * 1.0 / COUNT(DISTINCT invoice_no), 2) AS avg_order_value
FROM sales;

-- Q2. Monthly revenue, orders and customers
SELECT year_month,
       ROUND(SUM(revenue), 0) AS revenue,
       COUNT(DISTINCT invoice_no) AS orders,
       COUNT(DISTINCT customer_id) AS customers
FROM sales
GROUP BY year_month
ORDER BY year_month;

-- Q3. Top 10 customers by revenue
SELECT customer_id,
       ROUND(SUM(revenue), 0) AS revenue,
       COUNT(DISTINCT invoice_no) AS orders
FROM sales
GROUP BY customer_id
ORDER BY revenue DESC
LIMIT 10;

-- Q4. Revenue by country (top 10)
SELECT country,
       ROUND(SUM(revenue), 0) AS revenue,
       ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM sales), 1) AS pct_of_revenue
FROM sales
GROUP BY country
ORDER BY revenue DESC
LIMIT 10;

-- Q5. Repeat purchase rate (customers with more than one order)
SELECT COUNT(*) AS customers,
       SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
       ROUND(100.0 * SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS repeat_pct
FROM (SELECT customer_id, COUNT(DISTINCT invoice_no) AS orders
      FROM sales GROUP BY customer_id) t;

-- Q6. Top 10 products by revenue
SELECT stock_code, MIN(description) AS description,
       SUM(quantity) AS units, ROUND(SUM(revenue), 0) AS revenue
FROM sales
GROUP BY stock_code
ORDER BY revenue DESC
LIMIT 10;

-- Q7. Revenue by weekday
SELECT weekday, ROUND(SUM(revenue), 0) AS revenue, COUNT(DISTINCT invoice_no) AS orders
FROM sales
GROUP BY weekday
ORDER BY revenue DESC;

-- Q8. Revenue concentration by customer quintile
WITH cust AS (
    SELECT customer_id, SUM(revenue) AS revenue FROM sales GROUP BY customer_id
),
ranked AS (
    SELECT revenue, NTILE(5) OVER (ORDER BY revenue DESC, customer_id) AS bucket FROM cust
)
SELECT bucket AS revenue_quintile,
       COUNT(*) AS customers,
       ROUND(SUM(revenue), 0) AS revenue,
       ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM cust), 1) AS pct_of_revenue
FROM ranked
GROUP BY bucket
ORDER BY bucket;

-- Q9. RFM scores (R: 5 = most recent, F and M: 5 = highest)
DROP TABLE IF EXISTS rfm_sql;

CREATE TABLE rfm_sql AS
WITH snap AS (
    SELECT datetime(MAX(invoice_date), '+1 day') AS snapshot FROM sales
),
base AS (
    SELECT customer_id,
           CAST(julianday((SELECT snapshot FROM snap)) - julianday(MAX(invoice_date)) AS INTEGER) AS recency,
           COUNT(DISTINCT invoice_no) AS frequency,
           SUM(revenue)               AS monetary
    FROM sales
    GROUP BY customer_id
)
SELECT customer_id, recency, frequency, ROUND(monetary, 2) AS monetary,
       6 - NTILE(5) OVER (ORDER BY recency, customer_id) AS r_score,
       NTILE(5) OVER (ORDER BY frequency, customer_id) AS f_score,
       NTILE(5) OVER (ORDER BY monetary, customer_id) AS m_score
FROM base;

-- then view it (run this line separately, then click Write Changes with Ctrl+S to save the table)
SELECT * FROM rfm_sql ORDER BY monetary DESC LIMIT 10;