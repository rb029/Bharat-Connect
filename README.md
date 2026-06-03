# Bharat Connect Analytics Hub

End-to-end **Data Analyst portfolio project** for a rural & regional Indian
e-commerce marketplace. Built with **Python, Pandas, SQL, Streamlit, Plotly,
and scikit-learn**, with Power BI-style dashboards.

## What's inside

```
bharat-connect-analytics-hub/
├── data/                       # synthetic CSVs (generated)
├── sql/
│   └── analytics_queries.sql   # 15+ business queries (SQLite/Postgres)
├── notebooks/
│   └── 01_exploratory.ipynb    # EDA scaffold
├── app/
│   └── streamlit_app.py        # multi-page admin dashboard
├── generate_data.py            # synthetic data generator (seeded)
├── data_cleaning.py            # cleaning + KPI pipeline
├── forecasting.py              # ML sales forecasting (Linear + Seasonal)
├── requirements.txt
└── README.md
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Generate the synthetic dataset (~50k orders, 24 months)
python generate_data.py

# 2) Run the cleaning pipeline (produces data/clean/*.parquet + kpis.json)
python data_cleaning.py

# 3) Train and score the forecast model
python forecasting.py

# 4) Launch the dashboard
streamlit run app/streamlit_app.py
```

Open http://localhost:8501 — the dashboard mirrors the React version
deployed on Lovable and adds Plotly drill-downs.

## Analyses included

| Module | Question answered |
|---|---|
| Revenue analytics | Monthly GMV, rural vs urban, growth QoQ, AOV |
| Customer behaviour | Cohort retention, repeat rate, RFM segments |
| Seller performance | Top sellers, rating vs revenue, on-time delivery |
| Category trends | Share of GMV, contribution margin, top movers |
| Regional demand | State-wise heatmap, rural %, delivery efficiency |
| Forecasting | 6-month sales forecast with confidence band |

## Power BI

`sql/analytics_queries.sql` can be plugged into Power BI's PostgreSQL /
SQLite connector. The recommended star-schema modelling lives at the top
of that file.

## Tech stack

Python 3.10+ · Pandas · NumPy · SQLAlchemy · SQLite · scikit-learn ·
Streamlit · Plotly · Faker

## License

MIT — use freely for portfolio and learning.
