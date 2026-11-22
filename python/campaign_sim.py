from pathlib import Path
import pandas as pd

# ---------- 1. SETTINGS ----------
PROJECT = Path(__file__).resolve().parent.parent
DATA = PROJECT / "dataset" / "dataset_processed"

TARGET_SEGMENT = "At Risk"
YEARS_OBSERVED = 2.02          # 1 Dec 2009 to 9 Dec 2011

# ASSUMPTIONS (change these and re-run; they are not in the dataset)
DISCOUNT = 0.10                # win-back offer: 10% off
GROSS_MARGIN = 0.40            # profit as a share of list price BEFORE any discount (dataset has no cost data)
COST_PER_CONTACT = 1.00        # GBP per customer contacted (email/SMS tool, handling)
FIXED_COST = 500.00            # GBP one-off campaign cost (design, set-up)
ORDERS_AFTER = {               # orders a reactivated customer places in the next 12 months
    "Conservative (1 order)": 1,
    "Base (2 orders)": 2,
    "Optimistic (3 orders)": 3,
}
RESPONSE_RATES = [r / 100 for r in range(1, 21)]      # 1% to 20%

# ---------- 2. LOAD THE TARGET SEGMENT ----------
seg = pd.read_csv(DATA / "segment_summary.csv").set_index("Segment")
n = int(seg.loc[TARGET_SEGMENT, "Customers"])
aov = seg.loc[TARGET_SEGMENT, "AOV"]
past_spend = seg.loc[TARGET_SEGMENT, "Revenue"]
annual_value_at_stake = past_spend / YEARS_OBSERVED

total_cost = FIXED_COST + n * COST_PER_CONTACT
profit_per_order = aov * (GROSS_MARGIN - DISCOUNT)    # list price x (margin - discount)

# ---------- 3. SCENARIOS ----------
rows = []
for name, orders in ORDERS_AFTER.items():
    for rate in RESPONSE_RATES:
        reactivated = round(n * rate)
        revenue = reactivated * orders * aov * (1 - DISCOUNT)
        gross_profit = reactivated * orders * profit_per_order
        net_profit = gross_profit - total_cost
        rows.append({"Scenario": name, "OrdersAfter": orders, "ResponseRate": rate,
                     "Contacted": n, "Reactivated": reactivated,
                     "Revenue": round(revenue, 0), "GrossProfit": round(gross_profit, 0),
                     "CampaignCost": round(total_cost, 0), "NetProfit": round(net_profit, 0),
                     "ROI": round(net_profit / total_cost, 2)})
sim = pd.DataFrame(rows)

# break-even response rate for each scenario
be = []
for name, orders in ORDERS_AFTER.items():
    be.append({"Scenario": name, "BreakEvenResponseRate": total_cost / (n * orders * profit_per_order)})
breakeven = pd.DataFrame(be)

assumptions = pd.DataFrame([
    ["Target segment", TARGET_SEGMENT], ["Customers contacted", n],
    ["Average order value (GBP)", round(aov, 0)], ["Discount", f"{DISCOUNT:.0%}"],
    ["Gross margin on list price", f"{GROSS_MARGIN:.0%}"], ["Cost per contact (GBP)", COST_PER_CONTACT],
    ["Fixed campaign cost (GBP)", FIXED_COST], ["Total campaign cost (GBP)", round(total_cost, 0)],
], columns=["Assumption", "Value"])

sim.to_csv(DATA / "campaign_sim.csv", index=False)
breakeven.to_csv(DATA / "campaign_breakeven.csv", index=False)
assumptions.to_csv(DATA / "campaign_assumptions.csv", index=False)

# ---------- 4. PRINT ----------
pd.set_option("display.width", 200)
print(f"Target: {TARGET_SEGMENT} | customers: {n:,} | average order value: GBP {aov:,.0f}")
print(f"Past spend of this segment: GBP {past_spend:,.0f} | roughly GBP {annual_value_at_stake:,.0f} per year at the historical rate")
print(f"Profit per order after discount: GBP {profit_per_order:,.0f} (margin {GROSS_MARGIN:.0%} - discount {DISCOUNT:.0%} on list price)")
print(f"Total campaign cost: GBP {total_cost:,.0f}\n")
print("Break-even response rate:")
print(breakeven.assign(BreakEvenResponseRate=lambda d: (d.BreakEvenResponseRate * 100).round(2).astype(str) + "%").to_string(index=False))
print("\nBase scenario (2 orders):")
show = sim[(sim.Scenario == "Base (2 orders)") & (sim.ResponseRate.isin([0.02, 0.05, 0.10, 0.15, 0.20]))]
print(show[["ResponseRate", "Reactivated", "Revenue", "GrossProfit", "CampaignCost", "NetProfit", "ROI"]].to_string(index=False))
print("\nSaved: campaign_sim.csv, campaign_breakeven.csv, campaign_assumptions.csv in", DATA)