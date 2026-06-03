"""
generate_data.py — Synthetic dataset for Bharat Connect Analytics Hub.

Produces realistic customers, sellers, products, orders, order_items,
payments and deliveries CSVs in ./data/raw/.
"""
from __future__ import annotations
import os, random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED); np.random.seed(SEED)
fake = Faker("en_IN"); Faker.seed(SEED)

OUT = "data/raw"
os.makedirs(OUT, exist_ok=True)

STATES = ["Uttar Pradesh","Maharashtra","Bihar","West Bengal","Tamil Nadu",
          "Rajasthan","Karnataka","Gujarat","Madhya Pradesh","Odisha",
          "Punjab","Kerala","Assam","Jharkhand","Telangana"]
CATEGORIES = ["Agri Inputs","Handlooms","Groceries","Electronics","Apparel",
              "Home & Kitchen","Health & Wellness","Dairy & Poultry"]
PAYMENTS = ["UPI","Cash on Delivery","Card","Wallet","Net Banking"]

N_CUSTOMERS = 8_000
N_SELLERS   = 600
N_PRODUCTS  = 1_500
N_ORDERS    = 50_000
START = datetime(2024, 1, 1)
END   = datetime(2025, 12, 31)

def rand_date():
    days = (END - START).days
    return START + timedelta(days=random.randint(0, days),
                             seconds=random.randint(0, 86399))

print("Generating customers...")
customers = pd.DataFrame({
    "customer_id": [f"CUST{i:06d}" for i in range(N_CUSTOMERS)],
    "name": [fake.name() for _ in range(N_CUSTOMERS)],
    "state": np.random.choice(STATES, N_CUSTOMERS, p=np.linspace(2,1,len(STATES))/np.linspace(2,1,len(STATES)).sum()),
    "is_rural": np.random.choice([True, False], N_CUSTOMERS, p=[0.62, 0.38]),
    "signup_date": [rand_date().date() for _ in range(N_CUSTOMERS)],
    "age": np.random.randint(18, 65, N_CUSTOMERS),
})

print("Generating sellers...")
sellers = pd.DataFrame({
    "seller_id": [f"SLR{i:05d}" for i in range(N_SELLERS)],
    "seller_name": [fake.company() for _ in range(N_SELLERS)],
    "state": np.random.choice(STATES, N_SELLERS),
    "category_focus": np.random.choice(CATEGORIES, N_SELLERS),
    "rating": np.round(np.random.uniform(3.2, 4.95, N_SELLERS), 2),
    "joined_at": [rand_date().date() for _ in range(N_SELLERS)],
})

print("Generating products...")
products = pd.DataFrame({
    "product_id": [f"PRD{i:06d}" for i in range(N_PRODUCTS)],
    "product_name": [fake.catch_phrase()[:50] for _ in range(N_PRODUCTS)],
    "category": np.random.choice(CATEGORIES, N_PRODUCTS),
    "seller_id": np.random.choice(sellers["seller_id"], N_PRODUCTS),
    "unit_price": np.round(np.random.gamma(2.0, 350, N_PRODUCTS) + 50, 2),
    "cost_price": 0.0,
})
products["cost_price"] = np.round(products["unit_price"] * np.random.uniform(0.55, 0.85, N_PRODUCTS), 2)

print(f"Generating {N_ORDERS} orders...")
order_dates = [rand_date() for _ in range(N_ORDERS)]
orders = pd.DataFrame({
    "order_id": [f"ORD{i:07d}" for i in range(N_ORDERS)],
    "customer_id": np.random.choice(customers["customer_id"], N_ORDERS),
    "order_date": order_dates,
    "status": np.random.choice(["delivered","cancelled","returned"], N_ORDERS, p=[0.92, 0.05, 0.03]),
})

print("Generating order items...")
items_per_order = np.random.choice([1,2,3,4], N_ORDERS, p=[0.55, 0.28, 0.12, 0.05])
rows = []
for oid, n in zip(orders["order_id"], items_per_order):
    for _ in range(n):
        p = products.sample(1).iloc[0]
        qty = int(np.random.choice([1,2,3], p=[0.7, 0.22, 0.08]))
        rows.append({
            "order_id": oid,
            "product_id": p["product_id"],
            "seller_id": p["seller_id"],
            "quantity": qty,
            "unit_price": p["unit_price"],
            "line_total": round(p["unit_price"] * qty, 2),
        })
order_items = pd.DataFrame(rows)

print("Generating payments...")
payments = pd.DataFrame({
    "order_id": orders["order_id"],
    "method": np.random.choice(PAYMENTS, N_ORDERS, p=[0.42, 0.28, 0.12, 0.10, 0.08]),
    "amount": order_items.groupby("order_id")["line_total"].sum().reindex(orders["order_id"]).values,
})

print("Generating deliveries...")
cust_lookup = customers.set_index("customer_id")["is_rural"].to_dict()
delivery_days = []
for cid in orders["customer_id"]:
    base = np.random.uniform(3.5, 5.8) if cust_lookup[cid] else np.random.uniform(1.4, 2.9)
    delivery_days.append(round(base + np.random.normal(0, 0.4), 2))
deliveries = pd.DataFrame({
    "order_id": orders["order_id"],
    "delivery_days": delivery_days,
    "on_time": np.random.choice([True, False], N_ORDERS, p=[0.87, 0.13]),
})

# Save
customers.to_csv(f"{OUT}/customers.csv", index=False)
sellers.to_csv(f"{OUT}/sellers.csv", index=False)
products.to_csv(f"{OUT}/products.csv", index=False)
orders.to_csv(f"{OUT}/orders.csv", index=False)
order_items.to_csv(f"{OUT}/order_items.csv", index=False)
payments.to_csv(f"{OUT}/payments.csv", index=False)
deliveries.to_csv(f"{OUT}/deliveries.csv", index=False)

print(f"\nDone. Files written to {OUT}/")
print(f"  customers:   {len(customers):>7,}")
print(f"  sellers:     {len(sellers):>7,}")
print(f"  products:    {len(products):>7,}")
print(f"  orders:      {len(orders):>7,}")
print(f"  order_items: {len(order_items):>7,}")
