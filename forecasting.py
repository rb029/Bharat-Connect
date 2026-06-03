"""
forecasting.py — 6-month sales forecast.

Combines a linear trend with a monthly seasonal index. Uses time-series
cross-validation to report RMSE. Saves forecast to data/clean/forecast.csv.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import root_mean_squared_error

fact = pd.read_parquet("data/clean/fact_sales.parquet")
monthly = (fact.groupby("year_month")["line_total"].sum()
                .sort_index().rename("revenue").reset_index())
monthly["t"] = np.arange(len(monthly))
monthly["month"] = pd.to_datetime(monthly["year_month"]).dt.month

# Seasonal index (mean ratio per calendar month)
trend_fit = LinearRegression().fit(monthly[["t"]], monthly["revenue"])
monthly["trend"] = trend_fit.predict(monthly[["t"]])
monthly["seasonal_ratio"] = monthly["revenue"] / monthly["trend"]
seasonal_idx = monthly.groupby("month")["seasonal_ratio"].mean()

# CV (rolling)
errors = []
for split in range(6, len(monthly) - 1):
    train = monthly.iloc[:split]
    test  = monthly.iloc[split:split+1]
    m = LinearRegression().fit(train[["t"]], train["revenue"])
    pred = m.predict(test[["t"]]) * seasonal_idx[test["month"].iloc[0]]
    errors.append(root_mean_squared_error(test["revenue"], pred))
rmse = float(np.mean(errors))

# Forecast next 6 months
last_t = monthly["t"].iloc[-1]
last_date = pd.to_datetime(monthly["year_month"].iloc[-1])
future_t = np.arange(last_t + 1, last_t + 7)
future_dates = [last_date + pd.DateOffset(months=i) for i in range(1, 7)]
future_months = [d.month for d in future_dates]

base = trend_fit.predict(pd.DataFrame({"t": future_t}))
seasonal = np.array([seasonal_idx[m] for m in future_months])
forecast = base * seasonal

out = pd.DataFrame({
    "year_month": [d.strftime("%Y-%m") for d in future_dates],
    "forecast":   forecast.round(2),
    "lower_88":   (forecast * 0.88).round(2),
    "upper_112":  (forecast * 1.12).round(2),
})
out.to_csv("data/clean/forecast.csv", index=False)

print(f"Cross-validated RMSE: INR {rmse:,.0f}")
print("\nForecast - next 6 months:")
print(out.to_string(index=False))
print("\nWrote data/clean/forecast.csv")
