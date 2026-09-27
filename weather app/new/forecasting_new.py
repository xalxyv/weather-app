import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller


class ForecastEngine:
    def __init__(self, series):
        self.series = series

    def forecast(self, steps, method="auto"):
        if method == "seasonal":
            season_length = min(365 if len(self.series) > 500 else 52, len(self.series) // 2)
            season_length = max(season_length, 4)
            return pd.Series([
                self.series.iloc[-(season_length - (i % season_length))] for i in range(steps)
            ])

        elif method == "ets":
            if len(self.series) >= 2:
                model = ExponentialSmoothing(
                    self.series,
                    trend='add',
                    seasonal='add',
                    seasonal_periods=360,
                    damped_trend=True
                )
                fit = model.fit(
                    smoothing_level=0.5,
                    smoothing_trend=0.01,
                    smoothing_seasonal=0.5
                )
                return fit.forecast(steps=steps)
            return pd.Series([self.series.iloc[-1]] * steps)

        elif method == "arima":
            if len(self.series) < 10:
                return pd.Series([self.series.iloc[-1]] * steps)
            adf_result = adfuller(self.series)
            d = 0 if adf_result[1] <= 0.05 else 1
            best_aic = float("inf")
            best_model = None
            for p in range(0, 3):
                for q in range(0, 3):
                    try:
                        model = ARIMA(self.series, order=(p, d, q))
                        fit = model.fit()
                        if fit.aic < best_aic:
                            best_aic = fit.aic
                            best_model = fit
                    except Exception:
                        continue
            if best_model is not None:
                return best_model.forecast(steps=steps)
            return pd.Series([self.series.iloc[-1]] * steps)

        else:
            if len(self.series) >= 52:
                return self.forecast(steps, method="seasonal")
            return self.forecast(steps, method="ets")
