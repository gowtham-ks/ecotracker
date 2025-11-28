from flask import Flask, render_template, request
import requests
import pandas as pd

app = Flask(__name__)

# Default emission factors (kg CO2e per unit)
EMISSION_FACTORS = {
    "electricity_kwh": 0.475,
    "natural_gas_kwh": 0.185,
    "car_km": 0.120,
    "bus_km": 0.082,
    "train_km": 0.041,
    "flight_km": 0.255,
    "waste_landfill_kg": 1.9,
    "waste_recycle_kg": 0.1
}

def safe_float(value):
    """Convert safely to float; return 0.0 if empty or invalid."""
    try:
        if value is None or str(value).strip() == "":
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def get_live_electricity_factor():
    """Optional: fetch live carbon intensity for electricity."""
    try:
        r = requests.get("https://api.carbonintensity.org.uk/intensity", timeout=5)
        if r.status_code == 200:
            data = r.json()
            live_factor = data["data"][0]["intensity"]["actual"]
            if live_factor is not None:
                return live_factor / 1000  # gCO2 → kgCO2
    except Exception:
        pass
    return EMISSION_FACTORS["electricity_kwh"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/report", methods=["POST"])
def report():
    # Collect inputs safely
    e = safe_float(request.form.get("electricity"))
    g = safe_float(request.form.get("gas"))
    c = safe_float(request.form.get("car"))
    b = safe_float(request.form.get("bus"))
    t = safe_float(request.form.get("train"))
    f = safe_float(request.form.get("flight"))
    wl = safe_float(request.form.get("waste_landfill"))
    wr = safe_float(request.form.get("waste_recycle"))

    # Update electricity factor with live data (safe)
    EMISSION_FACTORS["electricity_kwh"] = get_live_electricity_factor()

    # --- Carbon footprint calculations ---
    energy = e * EMISSION_FACTORS["electricity_kwh"] + g * EMISSION_FACTORS["natural_gas_kwh"]
    transport = (
        c * EMISSION_FACTORS["car_km"]
        + b * EMISSION_FACTORS["bus_km"]
        + t * EMISSION_FACTORS["train_km"]
        + f * EMISSION_FACTORS["flight_km"]
    )
    waste = wl * EMISSION_FACTORS["waste_landfill_kg"] + wr * EMISSION_FACTORS["waste_recycle_kg"]
    total = energy + transport + waste

    df = pd.DataFrame({
        "Category": ["Energy", "Transport", "Waste"],
        "Emissions (kg CO2e)": [energy, transport, waste]
    })

    # Sustainability insights
    highest = df.loc[df["Emissions (kg CO2e)"].idxmax(), "Category"]
    insights = (
        f"Your highest emissions come from {highest.lower()}. "
        f"Consider improving your {highest.lower()} habits for a greener lifestyle."
    )

    return render_template(
        "report.html",
        total=round(total, 2),
        data=df.to_dict(orient="records"),
        insights=insights,
    )

if __name__ == "__main__":
    app.run(debug=True)
