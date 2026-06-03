"""
Bharat Connect Analytics Hub — Streamlit admin dashboard.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations
import json, os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Bharat Connect Analytics Hub",
    page_icon="📊",
    layout="wide",
)

CLEAN = "data/clean"
if not os.path.exists(f"{CLEAN}/fact_sales.parquet"):
    st.error("Run `python generate_data.py` and `python data_cleaning.py` first.")
    st.stop()

@st.cache_data
def load():
    fact = pd.read_parquet(f"{CLEAN}/fact_sales.parquet")
    with open(f"{CLEAN}/kpis.json") as f:
        kpis = json.load(f)
    forecast = pd.read_csv(f"{CLEAN}/forecast.csv") if os.path.exists(f"{CLEAN}/forecast.csv") else None
    return fact, kpis, forecast

fact, kpis, forecast = load()

# ---------- Header ----------
st.markdown("## 📊 Bharat Connect Analytics Hub")
st.caption("Rural & regional e-commerce intelligence · synthetic dataset")

# ---------- Filters ----------
with st.sidebar:
    st.header("Filters")
    states = ["All"] + sorted(fact["state"].dropna().unique().tolist())
    categories = ["All"] + sorted(fact["category"].dropna().unique().tolist())
    state_sel = st.selectbox("State", states)
    cat_sel   = st.selectbox("Category", categories)
    segment   = st.radio("Segment", ["All", "Rural", "Urban"], horizontal=True)

df = fact.copy()
if state_sel != "All": df = df[df["state"] == state_sel]
if cat_sel   != "All": df = df[df["category"] == cat_sel]
if segment == "Rural": df = df[df["is_rural"] == True]
if segment == "Urban": df = df[df["is_rural"] == False]

# ---------- KPIs ----------
def fmt_inr(n):
    if n >= 1e7: return f"₹{n/1e7:.2f} Cr"
    if n >= 1e5: return f"₹{n/1e5:.2f} L"
    return f"₹{n:,.0f}"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Revenue", fmt_inr(df["line_total"].sum()), f"{kpis['qoq_growth_pct']}% QoQ")
c2.metric("Orders", f"{df['order_id'].nunique():,}")
c3.metric("Customers", f"{df['customer_id'].nunique():,}")
c4.metric("AOV", fmt_inr(df["line_total"].sum() / max(df["order_id"].nunique(), 1)))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Active Sellers", f"{df['seller_id'].nunique():,}")
c6.metric("Rural Share", f"{kpis['rural_share_pct']}%")
c7.metric("On-time Delivery", f"{kpis['on_time_delivery_pct']}%")
c8.metric("Avg Delivery", f"{df['delivery_days'].mean():.2f} d")

st.divider()

tabs = st.tabs(["Revenue", "Customers", "Sellers", "Categories", "Regional", "Forecast"])

# ---------- Revenue ----------
with tabs[0]:
    monthly = (df.assign(seg=df["is_rural"].map({True: "Rural", False: "Urban"}))
                 .groupby(["year_month","seg"])["line_total"].sum().reset_index())
    fig = px.area(monthly, x="year_month", y="line_total", color="seg",
                  title="Monthly GMV — rural vs urban", labels={"line_total":"Revenue (INR)"})
    st.plotly_chart(fig, use_container_width=True)

    cA, cB = st.columns(2)
    with cA:
        pay = df.groupby("method")["line_total"].sum().reset_index()
        st.plotly_chart(px.pie(pay, values="line_total", names="method", title="Payment mix"),
                        use_container_width=True)
    with cB:
        dlv = (df.groupby(["year_month", df["is_rural"].map({True:"Rural",False:"Urban"})])
                 ["delivery_days"].mean().reset_index())
        dlv.columns = ["year_month","segment","avg_days"]
        st.plotly_chart(px.line(dlv, x="year_month", y="avg_days", color="segment",
                                title="Avg delivery days"), use_container_width=True)

# ---------- Customers ----------
with tabs[1]:
    orders_per_cust = df.groupby("customer_id")["order_id"].nunique()
    repeat_rate = (orders_per_cust > 1).mean() * 100
    st.metric("Repeat purchase rate", f"{repeat_rate:.1f}%")
    age_band = pd.cut(df["age"], bins=[17,25,35,45,55,65], labels=["18-25","26-35","36-45","46-55","56-65"])
    by_age = df.assign(age_band=age_band).groupby("age_band", observed=True)["line_total"].sum().reset_index()
    st.plotly_chart(px.bar(by_age, x="age_band", y="line_total", title="Revenue by age band"),
                    use_container_width=True)

# ---------- Sellers ----------
with tabs[2]:
    top = (df.groupby(["seller_id","seller_name"])
             .agg(revenue=("line_total","sum"),
                  orders=("order_id","nunique"),
                  on_time_pct=("on_time", lambda s: round(s.mean()*100,1)),
                  rating=("rating","first"))
             .reset_index().sort_values("revenue", ascending=False).head(20))
    st.dataframe(top, use_container_width=True, hide_index=True)
    st.plotly_chart(px.scatter(top, x="rating", y="revenue", size="orders",
                               hover_name="seller_name", title="Rating vs Revenue (top 20)"),
                    use_container_width=True)

# ---------- Categories ----------
with tabs[3]:
    by_cat = (df.groupby("category")
                .agg(revenue=("line_total","sum"), margin=("margin","sum"))
                .reset_index().sort_values("revenue", ascending=False))
    by_cat["margin_pct"] = (by_cat["margin"] / by_cat["revenue"] * 100).round(1)
    st.plotly_chart(px.bar(by_cat, x="revenue", y="category", orientation="h",
                           title="Category revenue"), use_container_width=True)
    st.dataframe(by_cat, use_container_width=True, hide_index=True)

# ---------- Regional ----------
with tabs[4]:
    by_state = (df.assign(seg=df["is_rural"].map({True:"Rural", False:"Urban"}))
                  .groupby(["state","seg"])["line_total"].sum().reset_index())
    st.plotly_chart(px.bar(by_state, x="state", y="line_total", color="seg",
                           title="State-wise revenue (stacked)"), use_container_width=True)

# ---------- Forecast ----------
with tabs[5]:
    if forecast is None:
        st.info("Run `python forecasting.py` to generate the forecast.")
    else:
        hist = (fact.groupby("year_month")["line_total"].sum()
                    .reset_index().rename(columns={"line_total":"actual"}))
        merged = pd.concat([
            hist.assign(forecast=None, lower_88=None, upper_112=None),
            forecast.assign(actual=None),
        ], ignore_index=True)
        fig = px.line(merged, x="year_month", y=["actual","forecast"],
                      title="6-month sales forecast (linear + seasonal)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(forecast, use_container_width=True, hide_index=True)

st.divider()
with st.expander("Download cleaned dataset"):
    st.download_button("fact_sales.csv (filtered)",
                       df.to_csv(index=False).encode(),
                       file_name="fact_sales_filtered.csv")
