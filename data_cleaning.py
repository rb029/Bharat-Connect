"""
data_cleaning.py — Cleaning + KPI pipeline.

Reads data/raw/*.csv, joins, cleans, and writes:
  - data/clean/fact_sales.parquet     (one row per order item, enriched)
  - data/clean/kpis.json              (headline KPIs for the dashboard)
"""
from __future__ import annotations
import os, json
try:
    import pandas as pd  # type: ignore
except ImportError as exc:
    raise ImportError("pandas is required to run this script. Install with pip install pandas") from exc

RAW   = "data/raw"
CLEAN = "data/clean"
os.makedirs(CLEAN, exist_ok=True)

print("Loading raw tables...")
customers  = pd.read_csv(f"{RAW}/customers.csv", parse_dates=["signup_date"])
sellers    = pd.read_csv(f"{RAW}/sellers.csv",   parse_dates=["joined_at"])
products   = pd.read_csv(f"{RAW}/products.csv")
orders     = pd.read_csv(f"{RAW}/orders.csv",    parse_dates=["order_date"])
items      = pd.read_csv(f"{RAW}/order_items.csv")
payments   = pd.read_csv(f"{RAW}/payments.csv")
deliveries = pd.read_csv(f"{RAW}/deliveries.csv")

print("Cleaning...")
# Drop cancelled / returned for revenue analysis
orders_delivered = orders[orders["status"] == "delivered"].copy()

fact = (items
    .merge(orders_delivered[["order_id","customer_id","order_date"]], on="order_id", how="inner")
    .merge(customers[["customer_id","state","is_rural","age"]], on="customer_id", how="left")
    .merge(products[["product_id","category","cost_price"]], on="product_id", how="left")
    .merge(sellers[["seller_id","seller_name","rating"]], on="seller_id", how="left")
    .merge(payments[["order_id","method"]], on="order_id", how="left")
    .merge(deliveries[["order_id","delivery_days","on_time"]], on="order_id", how="left")
)

fact["margin"] = fact["line_total"] - fact["cost_price"] * fact["quantity"]
fact["year_month"] = fact["order_date"].dt.to_period("M").astype(str)

print(f"Fact table: {len(fact):,} rows, {fact.shape[1]} cols")
fact.to_parquet(f"{CLEAN}/fact_sales.parquet", index=False)

print("Computing KPIs...")
total_revenue   = float(fact["line_total"].sum())
total_orders    = int(orders_delivered["order_id"].nunique())
active_customers= int(fact["customer_id"].nunique())
active_sellers  = int(fact["seller_id"].nunique())
aov             = total_revenue / total_orders
rural_share     = float(fact.loc[fact["is_rural"], "line_total"].sum() / total_revenue * 100)
on_time_rate    = float(fact["on_time"].mean() * 100)

# QoQ growth
monthly = fact.groupby("year_month")["line_total"].sum().sort_index()
last3, prev3 = monthly.iloc[-3:].sum(), monthly.iloc[-6:-3].sum()
qoq_growth = float((last3 - prev3) / prev3 * 100)

kpis = {
    "total_revenue": round(total_revenue, 2),
    "total_orders": total_orders,
    "active_customers": active_customers,
    "active_sellers": active_sellers,
    "avg_order_value": round(aov, 2),
    "rural_share_pct": round(rural_share, 2),
    "on_time_delivery_pct": round(on_time_rate, 2),
    "qoq_growth_pct": round(qoq_growth, 2),
}

with open(f"{CLEAN}/kpis.json", "w") as f:
    json.dump(kpis, f, indent=2)

print("\nHeadline KPIs:")
for k, v in kpis.items():
    print(f"  {k:25s} {v}")
print(f"\nWrote {CLEAN}/fact_sales.parquet and {CLEAN}/kpis.json")
