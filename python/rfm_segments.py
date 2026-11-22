import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd

# ---------- 1. SETTINGS ----------
PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "dataset" / "dataset_processed"
DB = PROJECT / "dataset" / "retail.db"

# ---------- 2. LOAD ----------
sales = pd.read_csv(DATA / "clean_sales.csv", parse_dates=["InvoiceDate"])
canc = pd.read_csv(DATA / "cancellations.csv")

# value of cancelled / returned goods per customer (cancellation rows have negative Quantity)
canc = canc.dropna(subset=["CustomerID"]).copy()
canc["CustomerID"] = canc["CustomerID"].astype(int)
canc["CancelledValue"] = (canc["Quantity"] * canc["UnitPrice"]).abs()
cancelled_by_customer = canc.groupby("CustomerID")["CancelledValue"].sum()

# ---------- 3. RFM VALUES ----------
# Snapshot date = the day after the last order in the data
snapshot = sales["InvoiceDate"].max() + pd.Timedelta(days=1)

rfm = sales.groupby("CustomerID").agg(
    Recency=("InvoiceDate", lambda x: (snapshot - x.max()).days),   # days since last order
    Frequency=("InvoiceNo", "nunique"),                             # number of orders
    MonetaryGross=("Revenue", "sum"),                               # total spend before cancellations
).reset_index()

rfm["Cancelled"] = rfm["CustomerID"].map(cancelled_by_customer).fillna(0)
rfm["Monetary"] = rfm["MonetaryGross"] - rfm["Cancelled"]          # net spend after cancellations

# ---------- 4. RFM SCORES (1 to 5) ----------
# rank(method="first") breaks ties so that qcut can make 5 equal-sized groups
rfm["R"] = pd.qcut(rfm["Recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["RFM_Score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

# ---------- 5. SEGMENTS (the first rule that matches wins, so the order matters) ----------
conditions = [
    (rfm.R >= 4) & (rfm.F >= 4) & (rfm.M >= 4),     # recent, frequent, high spend
    (rfm.R >= 3) & (rfm.F >= 3),                     # fairly recent and frequent
    (rfm.R >= 4) & (rfm.Frequency == 1),             # recent first-time buyers
    (rfm.R <= 2) & (rfm.F >= 3),                     # used to buy often, gone quiet
    (rfm.R <= 2) & (rfm.F <= 2),                     # long gone and rarely bought
]
names = ["Champions", "Loyal", "New Customers", "At Risk", "Lost"]
rfm["Segment"] = np.select(conditions, names, default="Need Attention")

# ---------- 6. SEGMENT SUMMARY ----------
order = ["Champions", "Loyal", "New Customers", "Need Attention", "At Risk", "Lost"]
seg = rfm.groupby("Segment").agg(
    Customers=("CustomerID", "count"),
    Revenue=("Monetary", "sum"),
    TotalOrders=("Frequency", "sum"),
    AvgRecencyDays=("Recency", "mean"),
    AvgOrders=("Frequency", "mean"),
    AvgSpend=("Monetary", "mean"),
).reindex(order).reset_index()
seg["PctCustomers"] = seg["Customers"] / seg["Customers"].sum()
seg["PctRevenue"] = seg["Revenue"] / seg["Revenue"].sum()
seg["AOV"] = seg["Revenue"] / seg["TotalOrders"]       # average order value = total revenue / total orders

# ---------- 7. SAVE ----------
rfm.to_csv(DATA / "rfm_customers.csv", index=False)
seg.to_csv(DATA / "segment_summary.csv", index=False)

# ---------- 8. PRINT ----------
pd.set_option("display.width", 200)
print("Snapshot date:", snapshot.date())
print(f"Customers: {len(rfm):,} | net revenue: {rfm['Monetary'].sum():,.0f} GBP")
print(f"Customers with net spend <= 0 after cancellations: {(rfm['Monetary'] <= 0).sum()}")
print("\nScore ranges:")
print("  Recency (days) by R score:\n", rfm.groupby("R")["Recency"].agg(["min", "max"]).T.to_string())
print("  Frequency (orders) by F score:\n", rfm.groupby("F")["Frequency"].agg(["min", "max"]).T.to_string())
print("\nSegment summary:")
print(seg.round({"Revenue": 0, "AvgRecencyDays": 0, "AvgOrders": 1, "AvgSpend": 0,
                 "PctCustomers": 3, "PctRevenue": 3, "AOV": 0}).to_string(index=False))

# ---------- 9. CROSS-CHECK against the SQL result (optional) ----------
try:
    con = sqlite3.connect(DB)
    sql = pd.read_sql("SELECT * FROM rfm_sql", con)
    con.close()
    m = rfm.merge(sql, left_on="CustomerID", right_on="customer_id")
    print("\nCross-check with SQL (rfm_sql table):")
    print("  Recency identical: ", (m["Recency"] == m["recency"]).mean() == 1)
    print("  Frequency identical:", (m["Frequency"] == m["frequency"]).mean() == 1)
    print("  Gross spend identical:", np.allclose(m["MonetaryGross"], m["monetary"], atol=0.01))
    print(f"  R score match: {(m['R'] == m['r_score']).mean():.2%} | F score match: {(m['F'] == m['f_score']).mean():.2%}")
except Exception as e:
    print("\n(Skipped SQL cross-check: run query Q9 in sql/analysis.sql first.)", e)
print("\nSaved: rfm_customers.csv and segment_summary.csv in", DATA)