import sqlite3
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB = PROJECT / "dataset" / "retail.db"

QUERY = """
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
       6 - NTILE(5) OVER (ORDER BY recency, customer_id)  AS r_score,
       NTILE(5) OVER (ORDER BY frequency, customer_id)    AS f_score,
       NTILE(5) OVER (ORDER BY monetary, customer_id)     AS m_score
FROM base;
"""

con = sqlite3.connect(DB)
con.executescript(QUERY)
con.commit()
print("rfm_sql table created with", con.execute("SELECT COUNT(*) FROM rfm_sql").fetchone()[0], "customers")
con.close()