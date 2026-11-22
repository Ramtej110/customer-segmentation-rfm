import sqlite3
from pathlib import Path
import pandas as pd

PROJECT = Path(__file__).resolve().parent.parent
CSV = PROJECT / "dataset" / "dataset_processed" / "clean_sales.csv"
DB = PROJECT / "dataset" / "retail.db"

df = pd.read_csv(CSV)
df.columns = ["invoice_no", "stock_code", "description", "quantity", "invoice_date",
              "unit_price", "customer_id", "country", "revenue", "year_month", "weekday"]
df["invoice_no"] = df["invoice_no"].astype(str)
df["stock_code"] = df["stock_code"].astype(str)

con = sqlite3.connect(DB)
df.to_sql("sales", con, if_exists="replace", index=False)
con.execute("CREATE INDEX idx_sales_customer ON sales(customer_id)")
con.execute("CREATE INDEX idx_sales_invoice ON sales(invoice_no)")
con.execute("CREATE INDEX idx_sales_month ON sales(year_month)")
con.commit()

print("Rows loaded:", con.execute("SELECT COUNT(*) FROM sales").fetchone()[0])
print("Customers:  ", con.execute("SELECT COUNT(DISTINCT customer_id) FROM sales").fetchone()[0])
print("Database saved to", DB)
con.close()