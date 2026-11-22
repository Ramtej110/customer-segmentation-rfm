from pathlib import Path
import pandas as pd

# ---------- 1. SETTINGS ----------
PROJECT = Path(__file__).resolve().parent.parent  
RAW_ROOT = PROJECT / "dataset" / "raw_dataset"            
OUT_FOLDER = PROJECT / "dataset" / "dataset_processed"
OUT_FOLDER.mkdir(parents=True, exist_ok=True)

log = []
def record(step, data):
    log.append({"step": step, "rows": len(data)})
    print(f"{step:<55} {len(data):>10,}")

# ---------- 2. LOAD every Excel file under raw_dataset ----------
files = [f for f in sorted(RAW_ROOT.rglob("*.xlsx")) if not f.name.startswith("~$")]
print(f"Found {len(files)} Excel file(s) under {RAW_ROOT}")
if len(files) != 2:
    print("WARNING: expected 2 files (one for 2009-2010, one for 2010-2011).")

frames = []
for file in files:
    print("Reading", file.relative_to(PROJECT), "(this can take a few minutes)...")
    part = pd.read_excel(file)
    part["InvoiceDate"] = pd.to_datetime(part["InvoiceDate"])
    print(f"   rows: {len(part):,} | dates: {part['InvoiceDate'].min():%d %b %Y} to {part['InvoiceDate'].max():%d %b %Y}")
    frames.append(part)

if not frames:
    raise SystemExit("No Excel files found under dataset/raw_dataset.")

df = pd.concat(frames, ignore_index=True)

# ---------- 3. RENAME columns ----------
df = df.rename(columns={"Invoice": "InvoiceNo",
                        "Price": "UnitPrice",
                        "Customer ID": "CustomerID"})
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
record("1. Raw rows (all files stacked)", df)

# ---------- 4. REMOVE DUPLICATES (also removes the Dec 2010 overlap) ----------
df = df.drop_duplicates()
record("2. After removing duplicate rows", df)

# ---------- 5. SEPARATE CANCELLATIONS ----------
is_cancel = df["InvoiceNo"].str.startswith("C")
cancellations = df[is_cancel].copy()
cancel_rate = cancellations["InvoiceNo"].nunique() / df["InvoiceNo"].nunique()
df = df[~is_cancel]
record("3. After removing cancellations", df)

# ---------- 6. DROP rows with no CustomerID ----------
no_id = df["CustomerID"].isna()
revenue_lost = (df.loc[no_id, "Quantity"] * df.loc[no_id, "UnitPrice"]).sum()
df = df.dropna(subset=["CustomerID"]).copy()
df["CustomerID"] = df["CustomerID"].astype(int)
record("4. After dropping missing CustomerID", df)

# ---------- 7. REMOVE invalid quantities and prices ----------
df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)].copy()
record("5. After removing Quantity<=0 or UnitPrice<=0", df)

# ---------- 8. NEW COLUMNS ----------
df["Revenue"] = df["Quantity"] * df["UnitPrice"]
df["YearMonth"] = df["InvoiceDate"].dt.to_period("M").astype(str)
df["Weekday"] = df["InvoiceDate"].dt.day_name()

# ---------- 9. SAVE ----------
df.to_csv(OUT_FOLDER / "clean_sales.csv", index=False)
cancellations.to_csv(OUT_FOLDER / "cancellations.csv", index=False)
pd.DataFrame(log).to_csv(OUT_FOLDER / "cleaning_log.csv", index=False)

# ---------- 10. SUMMARY ----------
print("\n--- Summary ---")
print(f"Cancellation rate (share of invoices):       {cancel_rate:.1%}")
print(f"Revenue on rows with no CustomerID dropped:  {revenue_lost:,.0f} GBP")
print(f"Final distinct customers:                    {df['CustomerID'].nunique():,}")
print(f"Final distinct invoices:                     {df['InvoiceNo'].nunique():,}")
print(f"Final revenue:                               {df['Revenue'].sum():,.0f} GBP")
print(f"Date range:                                  {df['InvoiceDate'].min()}  to  {df['InvoiceDate'].max()}")
print("Saved files in", OUT_FOLDER)
