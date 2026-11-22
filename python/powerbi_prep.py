from pathlib import Path
import pandas as pd

# ---------- 1. SETTINGS ----------
PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "dataset" / "dataset_processed"
OUT = PROJECT / "dataset" / "powerbi_ready"
OUT.mkdir(parents=True, exist_ok=True)

SEGMENT_ORDER = ["Champions", "Loyal", "New Customers", "Need Attention", "At Risk", "Lost"]
order_map = {name: i + 1 for i, name in enumerate(SEGMENT_ORDER)}

sales = pd.read_csv(SRC / "clean_sales.csv", usecols=["InvoiceNo", "CustomerID", "Revenue", "Country", "YearMonth"])
rfm = pd.read_csv(SRC / "rfm_customers.csv")
seg = pd.read_csv(SRC / "segment_clv.csv")

# ---------- 2. KPI (one row) ----------
gross = sales["Revenue"].sum()
orders = sales["InvoiceNo"].nunique()
kpi = pd.DataFrame([{
    "Customers": len(rfm),
    "Orders": orders,
    "GrossSales": round(gross, 2),
    "NetRevenue": round(rfm["Monetary"].sum(), 2),
    "AvgOrderValue": round(gross / orders, 2),
    "RepeatCustomerPct": round((rfm["Frequency"] > 1).mean(), 4),
}])
kpi.to_csv(OUT / "kpi.csv", index=False)

# ---------- 3. MONTHLY SALES ----------
monthly = sales.groupby("YearMonth").agg(GrossSales=("Revenue", "sum"),
                                         Orders=("InvoiceNo", "nunique"),
                                         Customers=("CustomerID", "nunique")).reset_index()
monthly["MonthStart"] = pd.to_datetime(monthly["YearMonth"] + "-01")
monthly["MonthType"] = monthly["YearMonth"].map(lambda m: "Partial month" if m == "2011-12" else "Full month")
monthly["GrossSales"] = monthly["GrossSales"].round(2)
monthly[["MonthStart", "GrossSales", "Orders", "Customers", "MonthType"]].to_csv(OUT / "monthly_sales.csv", index=False)

# ---------- 4. TOP 10 COUNTRIES ----------
country = sales.groupby("Country")["Revenue"].sum().sort_values(ascending=False).reset_index()
country["PctOfSales"] = (country["Revenue"] / country["Revenue"].sum()).round(4)
country = country.head(10).rename(columns={"Revenue": "GrossSales"})
country["GrossSales"] = country["GrossSales"].round(2)
country.to_csv(OUT / "country_sales.csv", index=False)

# ---------- 5. SEGMENTS ----------
seg = seg.rename(columns={"Revenue": "NetRevenue", "PctRevenue": "PctNetRevenue"})
seg.insert(1, "SegmentOrder", seg["Segment"].map(order_map))
seg = seg.sort_values("SegmentOrder")
seg = seg[["Segment", "SegmentOrder", "Customers", "PctCustomers", "NetRevenue", "PctNetRevenue",
           "AvgRecencyDays", "AvgOrders", "AvgSpend", "AOV", "OrdersPerYear", "AnnualValue", "CLV"]]
seg.round(4).to_csv(OUT / "segments.csv", index=False)

# ---------- 6. CUSTOMERS WITH SEGMENT ----------
rfm["SegmentOrder"] = rfm["Segment"].map(order_map)
rfm.round(2).to_csv(OUT / "rfm_customers.csv", index=False)

# ---------- 7. COHORT RETENTION (month as a real date) ----------
coh = pd.read_csv(SRC / "cohort_retention.csv")
coh["CohortMonth"] = pd.to_datetime(coh["CohortMonth"] + "-01")
coh.to_csv(OUT / "cohort_retention.csv", index=False)

# ---------- 8. COPY THE REST ----------
for name in ["retention_curve", "campaign_sim", "campaign_breakeven"]:
    pd.read_csv(SRC / f"{name}.csv").to_csv(OUT / f"{name}.csv", index=False)

# ---------- 9. REPORT ----------
print("Created in", OUT)
for f in sorted(OUT.glob("*.csv")):
    d = pd.read_csv(f)
    print(f"  {f.name:<24} {len(d):>6,} rows  columns: {', '.join(d.columns)}")
print("\nKPI row:")
print(kpi.to_string(index=False))