import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from datetime import date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import requests
import os
from forecasting_new import ForecastEngine


def forecast(series, steps, method="auto"):
    """Wrapper around ForecastEngine"""
    return ForecastEngine(series).forecast(steps, method=method)

def get_current_weather_open_meteo(city):
    """Fetch current weather from Open-Meteo API using city name."""
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_data = requests.get(geo_url, timeout=10).json()
        if not geo_data.get('results'):
            return None
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        temp = requests.get(weather_url, timeout=10).json()['current_weather']['temperature']
        return temp
    except Exception:
        return None

def prepare_forecasting_dataset(csv_path, target_column='avr_Temp'):
    """
    Reads the CSV file, extracts all metadata, and returns a pandas Series ready for forecasting,
    along with metadata about the dataset.

    Args:
        csv_path (str): Path to the CSV file.
        target_column (str): The column to use as the target time series (default: 'avr_Temp').

    Returns:
        tuple: (time series for forecasting, metadata dictionary)
    """
    df = pd.read_csv(csv_path, parse_dates=['date'], dayfirst=True)
    df.set_index('date', inplace=True)
    metadata = {
        'columns': df.columns.tolist(),
        'dtypes': df.dtypes.apply(lambda x: str(x)).to_dict(),
        'num_rows': len(df),
        'index_name': df.index.name,
        'index_type': str(df.index.dtype),
        'head': df.head(3).to_dict(),
        'df': df  # include the full DataFrame for reference if needed
    }
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in CSV.")
    series = df[target_column]
    return series, metadata


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Multi-Screen Weather App")
        self.geometry("800x600")
        self.configure(bg="darkblue")
        self.series = None  # forecasting series
        self.metadata = None  # metadata dict
        self.pred = None
        self.forecast_date_used = None  # Track which date the prediction is for
        self.forecast_method = "auto"
        self.user_type = None
        container = tk.Frame(self, bg="darkblue")
        container.place(relx=0.5, rely=0.5, anchor="center")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (LoginPage, HomePage, WeatherPage, ComparePage, PredictionViewPage):
            page = F(container, self)
            self.frames[F] = page
            page.grid(row=0, column=0, sticky="nsew")
        self.show_frame(LoginPage)

    def show_frame(self, frame_class):
        frame = self.frames[frame_class]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()


class LoginPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="darkblue")
        self.controller = controller
        tk.Label(self, text="Weather App Login", fg="white", bg="darkblue", font=("Arial", 24, "bold")).pack(pady=40)
        tk.Label(self, text="Username:", fg="white", bg="darkblue", font=("Arial", 12)).pack(pady=(20,5))
        self.username_entry = tk.Entry(self, font=("Arial", 12), width=25)
        self.username_entry.pack(pady=5)
        tk.Label(self, text="Password:", fg="white", bg="darkblue", font=("Arial", 12)).pack(pady=(10,5))
        self.password_entry = tk.Entry(self, show="*", font=("Arial", 12), width=25)
        self.password_entry.pack(pady=5)
        self.error_label = tk.Label(self, text="", fg="red", bg="darkblue", font=("Arial", 10))
        self.error_label.pack(pady=5)
        tk.Button(self, text="Admin Login", command=self.admin_login, bg="white", fg="darkblue", font=("Arial", 12, "bold"), width=20).pack(pady=15)
        tk.Button(self, text="Guest Login", command=self.guest_login, bg="lightblue", fg="darkblue", font=("Arial", 12, "bold"), width=20).pack(pady=5)
        self.username_entry.bind('<Return>', lambda e: self.admin_login())
        self.password_entry.bind('<Return>', lambda e: self.admin_login())

    def admin_login(self):
        if self.username_entry.get() == "OCR" and self.password_entry.get() == "2139":
            self.error_label.config(text="Admin login successful!", fg="green")
            self.clear_fields()
            self.controller.user_type = "admin"
            self.controller.show_frame(HomePage)
        else:
            self.error_label.config(text="Invalid credentials! Try again or use Guest Login.", fg="red")
            self.password_entry.delete(0, tk.END)

    def guest_login(self):
        self.error_label.config(text="Guest login successful!", fg="green")
        self.clear_fields()
        self.controller.user_type = "guest"
        self.controller.show_frame(HomePage)

    def clear_fields(self):
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.after(1500, lambda: self.error_label.config(text=""))


class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="darkblue")
        self.controller = controller
        self.pane = tk.Frame(self, bg="darkblue")
        self.pane.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(self.pane, text="Location:", fg="white", bg="darkblue").pack(anchor="center", pady=(0, 20))
        self.location = ttk.Combobox(self.pane, values=["London"], state="readonly")
        self.location.current(0)
        self.location.pack(fill="x", pady=(0, 20), padx=30)
        self.load_csv_btn = tk.Button(self.pane, text="Load CSV", command=self.load_csv_file, bg="white", fg="darkblue")
        self.load_csv_btn.pack(fill="x", pady=10, padx=30)
        tk.Button(self.pane, text="Go to Weather Prediction", command=lambda: controller.show_frame(WeatherPage), bg="white", fg="darkblue").pack(fill="x", pady=10, padx=30)
        tk.Button(self.pane, text="Future Predictions", command=lambda: controller.show_frame(PredictionViewPage), bg="white", fg="darkblue").pack(fill="x", pady=10, padx=30)

    def on_show(self):
        dirname = os.path.dirname(__file__)
        filename= os.path.join(dirname, 'resources/1979-2025.csv')
        if self.controller.user_type == "admin":
            self.load_csv_btn.pack(fill="x", pady=10, padx=30)
        else:
            self.load_csv_btn.pack_forget()
            if self.controller.series is None:
                try:
                    series, metadata = prepare_forecasting_dataset(filename)
                    self.controller.series = series
                    self.controller.metadata = metadata
                    messagebox.showinfo("Loaded", f"Guest CSV loaded automatically. Data covers {len(series)} days.")
                except Exception as e:
                    messagebox.showerror("Error", f"Guest CSV load failed: {e}")

    def load_csv_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files","*.csv")])
        if not path: return
        try:
            series, metadata = prepare_forecasting_dataset(path)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.controller.series = series
        self.controller.metadata = metadata
        messagebox.showinfo("Loaded", f"CSV loaded successfully\nData covers {len(series)} days")


class WeatherPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="darkblue")
        self.controller = controller
        self.auto_forecast_done = False
        tk.Label(self, text="Weather Prediction Screen", fg="white", bg="darkblue", font=("Arial", 18)).pack(pady=20)
        self.today_text = tk.Text(self, width=50, height=2, font=("Arial", 18), wrap="none")
        self.today_text.tag_configure("center", justify="center")
        self.today_text.pack(pady=(10, 0))
        tk.Label(self, text="Forecast Method:", fg="white", bg="darkblue").pack()
        self.method_var = tk.StringVar(value="auto")
        method_frame = tk.Frame(self, bg="darkblue")
        method_frame.pack(pady=5)
        methods = [("Auto (Recommended)", "auto"), ("Seasonal Pattern", "seasonal"), ("Exponential Smoothing", "ets"), ("ARIMA", "arima")]
        for text, value in methods:
            tk.Radiobutton(method_frame, text=text, variable=self.method_var, value=value, fg="white", bg="darkblue", selectcolor="navy").pack(anchor="w")
        tk.Label(self, text="Forecast Until Date:", fg="white", bg="darkblue", font=("Arial", 12)).pack(pady=(20,5))
        self.forecast_date = DateEntry(self, date_pattern="yyyy-mm-dd")
        self.forecast_date.pack()
        self.weeks_label = tk.Label(self, text="Days to forecast: -", fg="yellow", bg="darkblue", font=("Arial", 10))
        self.weeks_label.pack(pady=5)
        tk.Button(self, text="Calculate Days", command=lambda: self.calculate_days(controller), bg="lightblue", fg="darkblue").pack(pady=5)
        tk.Button(self, text="Run Forecast", command=lambda: self.run_forecast(controller), bg="white", fg="darkblue").pack(pady=10)
        tk.Button(self, text="Show Graph", command=lambda: self.show_graph(controller), bg="white", fg="darkblue").pack(pady=10)
        tk.Button(self, text="Compare with Live Weather", command=self.compare_with_live_weather, bg="lightgreen", fg="darkblue").pack(pady=10)
        tk.Button(self, text="Back to Home", command=lambda: controller.show_frame(HomePage), bg="white", fg="darkblue").pack(pady=20)

    def on_show(self):
        if not self.auto_forecast_done and self.controller.series is not None:
            self.auto_forecast_done = True
            self.forecast_date.set_date(date.today())
            self.calculate_days(self.controller)
            self.run_forecast(self.controller)

    def calculate_days(self, controller):
        forecast_end = self.forecast_date.get_date()
        days = (forecast_end - date.today()).days
        if days == 0:
            self.weeks_label.config(text=f"Selected date is today")
        elif days < 0:
            self.weeks_label.config(text=f"Selected date is {abs(days)} days in the past")
        else:
            self.weeks_label.config(text=f"Days to forecast: {days} days")

    def run_forecast(self, controller):
        if controller.series is None:
            messagebox.showerror("Error", "Load CSV first")
            return
        series = controller.series.copy()
        method = self.method_var.get()
        controller.forecast_method = method
        forecast_target_date = self.forecast_date.get_date()
        
        #  Use actual last date from series instead of the permenate date
        dataset_last_date = series.index[-1].date()
        
        # Calculate days from end of dataset to target date
        steps = (forecast_target_date - dataset_last_date).days
        steps = max(1, steps)
        
        # Update series with current weather if available
        today_temp = get_current_weather_open_meteo(controller.frames[HomePage].location.get())
        if today_temp is not None and dataset_last_date == date.today():
            series.iloc[-1] = today_temp
        
        # Generate forecast
        controller.pred = forecast(series, steps, method=method)
        controller.forecast_date_used = forecast_target_date
        
        # Get the correct predicted value for the target date
        # The last value in predict the target date
        predicted_value = controller.pred.iloc[-1]
        
        self.today_text.delete("1.0", tk.END)
        self.today_text.insert(tk.END, f"Forecast for {forecast_target_date}: {predicted_value:.2f}°C", "center")
        messagebox.showinfo("Forecast Complete", f"Forecast method: {method}\nPredicted temperature for {forecast_target_date}: {predicted_value:.2f}°C")

    def show_graph(self, controller):
        if controller.series is None:
            messagebox.showerror("Error", "Load CSV first")
            return
        series = controller.series
        last_date = series.index[-1]
        today_date = pd.Timestamp(date.today())
        
        plt.figure(figsize=(14,7))
        # Plot actuals
        plt.plot(series.index, series.values, label="Actual", linewidth=1.5, marker='o', markersize=3, alpha=0.8, color='blue')
        
        # Properly forecast from day after last_date to today
        days_to_forecast = (today_date - last_date).days
        if days_to_forecast > 0:
            # Generate fresh forecast for each day up to today
            forecasted = []
            for i in range(1, days_to_forecast + 1):
                pred = forecast(series, i, method=controller.forecast_method if hasattr(controller, 'forecast_method') else 'auto')
                forecasted.append(pred.iloc[-1])  # Take the last (target) value
            
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days_to_forecast, freq='D')
            plt.plot(future_dates, forecasted, label="Forecast (to today)", linewidth=1.5, linestyle='--', color='orange', marker='o', markersize=6)
        
        plt.title("Temperature: Actuals and Forecast to Today", fontsize=16, fontweight='bold')
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Average Temperature (°C)", fontsize=12)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.show()

    def compare_with_live_weather(self):
        city = self.controller.frames[HomePage].location.get()
        live_temp = get_current_weather_open_meteo(city)
        if live_temp is None:
            messagebox.showerror("Error", "Could not fetch live weather data")
            return
        if self.controller.pred is not None:
            # Only compare if the forecast was for today
            if self.controller.forecast_date_used == date.today():
                predicted_temp = self.controller.pred.iloc[-1]
                diff = live_temp - predicted_temp
                msg = (
                    f"Live temperature in {city}: {live_temp:.2f}°C\n"
                    f"Predicted for today: {predicted_temp:.2f}°C\n"
                    f"Difference (Live - Predicted): {diff:+.2f}°C"
                )
                messagebox.showinfo("Live vs Prediction", msg)
            else:
                messagebox.showinfo("Info", f"Current live temperature in {city}: {live_temp:.2f}°C\n\nNote: Your forecast is for {self.controller.forecast_date_used}, not today.")
        else:
            messagebox.showinfo("Info", f"Current live temperature in {city}: {live_temp:.2f}°C")


class ComparePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="darkblue")
        tk.Label(self, text="Data Comparison Screen", fg="white", bg="darkblue", font=("Arial", 18)).pack(pady=20)
        tk.Button(self, text="Show Comparison", command=lambda: self.compare(controller), bg="white", fg="darkblue").pack(pady=10)
        tk.Button(self, text="Back to Home", command=lambda: controller.show_frame(HomePage), bg="white", fg="darkblue").pack(pady=10)
        self.text = tk.Text(self, width=80, height=20)
        self.text.pack(pady=10)

    def compare(self, controller):
        if controller.series is None or controller.pred is None:
            messagebox.showerror("Error", "Run forecast first")
            return
        series = controller.series
        n = len(controller.pred)
        test = series.iloc[-n:]
        pred = controller.pred
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, f"Forecast Method: {controller.forecast_method}\n{'='*60}\n\n")
        for i in range(n):
            self.text.insert(tk.END, f"Index {test.index[i]}  Actual: {test.values[i]:.3f}  Predicted: {pred.iloc[i]:.3f}\n")


class PredictionViewPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="darkblue")
        tk.Label(self, text="Future Weather Prediction", fg="white", bg="darkblue", font=("Arial", 18)).pack(pady=20)
        interval_frame = tk.Frame(self, bg="darkblue")
        interval_frame.pack(pady=10)
        tk.Label(interval_frame, text="Prediction Interval:", fg="white", bg="darkblue", font=("Arial", 12)).pack()
        self.interval_var = tk.StringVar(value="daily")
        interval_options = tk.Frame(interval_frame, bg="darkblue")
        interval_options.pack()
        tk.Radiobutton(interval_options, text="Daily", variable=self.interval_var, value="daily", fg="white", bg="darkblue", selectcolor="navy", font=("Arial", 10)).pack(side="left", padx=10)
        tk.Radiobutton(interval_options, text="Weekly", variable=self.interval_var, value="weekly", fg="white", bg="darkblue", selectcolor="navy", font=("Arial", 10)).pack(side="left", padx=10)

        date_frame = tk.Frame(self, bg="darkblue")
        date_frame.pack(pady=10)
        tk.Label(date_frame, text="From Date:", fg="white", bg="darkblue").grid(row=0,column=0,padx=5,pady=5)
        self.from_date = DateEntry(date_frame, date_pattern="yyyy-mm-dd", state="readonly")
        self.from_date.set_date(date.today())
        self.from_date.grid(row=0,column=1,padx=5,pady=5)
        tk.Label(date_frame, text="To Date:", fg="white", bg="darkblue").grid(row=1,column=0,padx=5,pady=5)
        self.to_date = DateEntry(date_frame, date_pattern="yyyy-mm-dd", mindate=date.today())
        self.to_date.grid(row=1,column=1,padx=5,pady=5)

        button_frame = tk.Frame(self, bg="darkblue")
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Generate Predictions", command=lambda: self.generate_predictions(controller), bg="white", fg="darkblue").grid(row=0,column=0,padx=5)
        tk.Button(button_frame, text="Show Graph", command=lambda: self.show_prediction_graph(controller), bg="lightblue", fg="darkblue").grid(row=0,column=1,padx=5)
        tk.Button(button_frame, text="Back to Home", command=lambda: controller.show_frame(HomePage), bg="white", fg="darkblue").grid(row=0,column=2,padx=5)

        tk.Label(self, text="Predicted Temperatures:", fg="white", bg="darkblue", font=("Arial", 12)).pack(pady=(20,5))
        text_frame = tk.Frame(self, bg="darkblue")
        text_frame.pack(pady=10, padx=20, fill="both", expand=True)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        self.results_text = tk.Text(text_frame, width=70, height=15, yscrollcommand=scrollbar.set)
        self.results_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.results_text.yview)
        self.prediction_dates = []
        self.prediction_temps = []

    def generate_predictions(self, controller):
        if controller.series is None:
            messagebox.showerror("Error", "Load CSV first")
            return
        from_date = self.from_date.get_date()
        to_date = self.to_date.get_date()
        if from_date > to_date:
            messagebox.showerror("Error", "From date must be before To date")
            return
        
        interval = self.interval_var.get()
        series = controller.series
        method = controller.forecast_method if controller.forecast_method else "auto"
        
        #  Calculate steps from dataset end, not from today
        dataset_last_date = series.index[-1].date()
        max_steps_needed = (to_date - dataset_last_date).days + 1
        
        # Generate all predictions we need
        predictions = forecast(series, max_steps_needed, method=method)
        
        self.prediction_dates, self.prediction_temps = [], []
        current_date = from_date
        delta = timedelta(days=1) if interval=="daily" else timedelta(days=7)
        
        while current_date <= to_date:
            #  Calculate index from dataset end, not from today
            days_from_dataset_end = (current_date - dataset_last_date).days
            
            if days_from_dataset_end > 0 and days_from_dataset_end <= len(predictions):
                # Prediction index (0-based, so subtract 1)
                pred_index = days_from_dataset_end - 1
                self.prediction_dates.append(current_date)
                self.prediction_temps.append(predictions.iloc[pred_index])
            elif days_from_dataset_end <= 0:
                # Date is in the historical data
                if current_date in series.index.date:
                    self.prediction_dates.append(current_date)
                    actual_value = series[series.index.date == current_date].iloc[0]
                    self.prediction_temps.append(actual_value)
            
            current_date += delta

        # Display
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert(tk.END, f"Prediction Method: {method}\nPrediction Interval: {interval.title()}\nDate Range: {from_date} to {to_date}\n{'='*60}\n\n")
        for d, t in zip(self.prediction_dates, self.prediction_temps):
            self.results_text.insert(tk.END, f"{d} ({d.strftime('%A')}): {round(t)}°C\n")
        messagebox.showinfo("Success", f"Generated predictions for {len(self.prediction_dates)} {interval}(s)")

    def show_prediction_graph(self, controller):
        if not self.prediction_dates or not self.prediction_temps:
            messagebox.showerror("Error", "Generate predictions first")
            return
        interval = self.interval_var.get()
        xLabels = [d.strftime("%Y-%m-%d") for d in self.prediction_dates]
        step = max(1, len(xLabels)//20)
        plt.figure(figsize=(14,7))
        plt.plot(range(len(self.prediction_temps)), self.prediction_temps, marker='o', linewidth=2, markersize=6, color='orange', label='Predicted Temperature')
        plt.xticks(range(0,len(xLabels),step), [xLabels[i] for i in range(0,len(xLabels),step)], rotation=45, ha='right')
        plt.title(f"Temperature Predictions ({interval.title()})\n{self.prediction_dates[0]} to {self.prediction_dates[-1]}", fontsize=16, fontweight='bold')
        plt.xlabel("Date" if interval=="daily" else "Week", fontsize=12)
        plt.ylabel("Temperature (°C)", fontsize=12)
        plt.legend(fontsize=11)
        plt.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    app = App()
    app.mainloop()