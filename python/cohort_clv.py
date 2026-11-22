from pathlib import Path
import pandas as pd

# ---------- 1. SETTINGS ----------
PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "dataset" / "dataset_processed"

LAST_FULL_MONTH = pd.Period("2011-11", "M")     # the data stops on 9 Dec 2011, so December 2011 is incomplete
EXISTING_BASE_COHORT = pd.Period("2009-12", "M")  # the first month of data: includes customers who joined earlier

sales = pd.read_csv(DATA / "clean_sales.csv", parse_dates=["InvoiceDate"])
seg = pd.read_csv(DATA / "segment_summary.csv")

# ---------- 2. COHORT RETENTION ----------
sales["OrderMonth"] = sales["InvoiceDate"].dt.to_period("M")
full = sales[sales["OrderMonth"] <= LAST_FULL_MONTH].copy()       # drop the incomplete last month

# each customer's cohort = the month of their first purchase in the data
first_month = full.groupby("CustomerID")["OrderMonth"].min().rename("CohortMonth")
full = full.join(first_month, on="CustomerID")
full["MonthIndex"] = (full["OrderMonth"] - full["CohortMonth"]).apply(lambda x: x.n)   # months since first purchase

active = (full.groupby(["CohortMonth", "MonthIndex"])["CustomerID"]
              .nunique().reset_index(name="ActiveCustomers"))
matrix = active.pivot(index="CohortMonth", columns="MonthIndex", values="ActiveCustomers")
cohort_size = matrix[0]
retention = matrix.div(cohort_size, axis=0)

# long format for Power BI
long = retention.round(4).reset_index().melt(id_vars="CohortMonth", var_name="MonthIndex", value_name="Retention").dropna()
long["CohortSize"] = long["CohortMonth"].map(cohort_size).astype(int)
long["ActiveCustomers"] = (long["Retention"] * long["CohortSize"]).round().astype(int)
long["CohortType"] = long["CohortMonth"].apply(lambda m: "Existing base" if m == EXISTING_BASE_COHORT else "New customers")
long["CohortMonth"] = long["CohortMonth"].astype(str)
long = long[["CohortMonth", "CohortType", "MonthIndex", "CohortSize", "ActiveCustomers", "Retention"]]

# average retention curve for genuinely new customers (excludes the first cohort)
new_only = retention.drop(index=EXISTING_BASE_COHORT)
curve = pd.DataFrame({"AvgRetention": new_only.mean(), "CohortsCounted": new_only.count()}).reset_index()
curve = curve[curve["MonthIndex"] > 0]

long.to_csv(DATA / "cohort_retention.csv", index=False)
retention.round(3).to_csv(DATA / "cohort_matrix.csv")
curve.to_csv(DATA / "retention_curve.csv", index=False)

# ---------- 3. ANNUAL RETENTION AND A SIMPLE CLV ----------
year = sales["InvoiceDate"].dt.year
active_2010 = set(sales.loc[year == 2010, "CustomerID"])
active_2011 = set(sales.loc[year == 2011, "CustomerID"])
annual_retention = len(active_2010 & active_2011) / len(active_2010)   # bought in 2010 and again in 2011

years_observed = (sales["InvoiceDate"].max() - sales["InvoiceDate"].min()).days / 365.25
lifespan_years = 1 / (1 - annual_retention)                            # simple churn-based lifespan

# CLV = average order value x orders per year x expected lifespan
seg["OrdersPerYear"] = seg["AvgOrders"] / years_observed
seg["AnnualValue"] = seg["AOV"] * seg["OrdersPerYear"]
seg["CLV"] = seg["AnnualValue"] * lifespan_years
seg.to_csv(DATA / "segment_clv.csv", index=False)

# ---------- 4. PRINT ----------
pd.set_option("display.width", 200)
print(f"Cohorts: {len(cohort_size)} (Dec 2009 to Nov 2011). Dec 2011 excluded (incomplete month).")
print("\nCohort sizes (customers whose first purchase was in that month):")
print(cohort_size.astype(int).to_string())
print("\nRetention curve for new customers (average across cohorts):")
print(curve[curve["MonthIndex"].isin([1, 2, 3, 6, 9, 12])].round(3).to_string(index=False))
print(f"\nDec 2009 'existing base' cohort, month 1 / 6 / 12 retention: "
      f"{retention.loc[EXISTING_BASE_COHORT, 1]:.1%} / {retention.loc[EXISTING_BASE_COHORT, 6]:.1%} / {retention.loc[EXISTING_BASE_COHORT, 12]:.1%}")
print(f"\nCustomers active in 2010: {len(active_2010):,} | of them active again in 2011: {len(active_2010 & active_2011):,} "
      f"({annual_retention:.1%})")
print(f"Years of data: {years_observed:.2f} | assumed lifespan = 1 / (1 - {annual_retention:.3f}) = {lifespan_years:.2f} years")
print("\nSegment value estimates (GBP):")
print(seg[["Segment", "Customers", "AOV", "OrdersPerYear", "AnnualValue", "CLV"]]
      .round({"AOV": 0, "OrdersPerYear": 1, "AnnualValue": 0, "CLV": 0}).to_string(index=False))
print("\nSaved: cohort_retention.csv, cohort_matrix.csv, retention_curve.csv, segment_clv.csv in", DATA)