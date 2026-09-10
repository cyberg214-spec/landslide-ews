"""
dynamic_risk.py
Rule-based dynamic risk scoring for SIH 26001 (replaces the LSTM from the
original team plan — explainable to judges, no training needed, and just
as valid a hackathon choice as the doc's own rule-based fallback option).

This will be imported by the backend (Phase 3) to turn live sensor readings
into a 0-1 risk_score, and to decide when to fire a "critical" alert.

Thresholds loosely follow IMD rainfall intensity categories:
  - Heavy rain: >64.5mm/24h continues to be the trigger the backend logic
    should escalate on. Docs: https://mausam.imd.gov.in/
"""

import os
import pandas as pd

# Find the project root (the folder containing "data/") regardless of
# whether this script is run from sih26001/ or sih26001/ml/
def _find_data_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in [here, os.path.dirname(here)]:
        if os.path.isdir(os.path.join(candidate, "data")):
            return os.path.join(candidate, "data")
    # default: assume a data/ folder next to this script's parent
    return os.path.join(os.path.dirname(here), "data")

# Tunable thresholds — documented so you can defend these numbers to judges
RAINFALL_HEAVY_MM = 64.5      # IMD "heavy rain" 24h threshold
RAINFALL_VERY_HEAVY_MM = 115.5  # IMD "very heavy rain" 24h threshold
SOIL_MOISTURE_SATURATED = 80.0  # percent
TILT_DRIFT_WARNING_DEG = 0.15   # cumulative drift from baseline
TILT_DRIFT_CRITICAL_DEG = 0.5


def calculate_dynamic_risk(soil_moisture, pore_water_pressure, tilt_x, tilt_y, rainfall_24h):
    """
    Combines four live signals into one 0-1 dynamic risk score.
    Each component is weighted by how directly it indicates imminent failure
    (tilt is the most direct precursor signal; rainfall is the least direct).
    """
    rainfall_component = min(rainfall_24h / RAINFALL_VERY_HEAVY_MM, 1.0)
    moisture_component = min(soil_moisture / SOIL_MOISTURE_SATURATED, 1.0)
    pressure_component = min(pore_water_pressure / 100.0, 1.0)

    tilt_magnitude = (tilt_x ** 2 + tilt_y ** 2) ** 0.5
    tilt_component = min(tilt_magnitude / TILT_DRIFT_CRITICAL_DEG, 1.0)

    # Tilt is weighted heaviest — it's the most direct physical precursor.
    # Rainfall/moisture/pressure are the "why it might happen", tilt is "it's happening".
    risk_score = (
        0.15 * rainfall_component
        + 0.20 * moisture_component
        + 0.20 * pressure_component
        + 0.45 * tilt_component
    )
    return round(min(risk_score, 1.0), 3)


def risk_label_from_score(score):
    if score < 0.25:
        return "low"
    elif score < 0.5:
        return "moderate"
    elif score < 0.75:
        return "high"
    else:
        return "critical"


def should_fire_alert(soil_moisture, tilt_x, tilt_y, rainfall_24h):
    """
    Explicit alert-trigger logic (separate from the continuous score) —
    matches the original spec: "if rainfall > X AND soil_moisture > Y AND
    tilt drift detected -> escalate + create alert".
    """
    tilt_magnitude = (tilt_x ** 2 + tilt_y ** 2) ** 0.5
    heavy_rain = rainfall_24h > RAINFALL_HEAVY_MM
    saturated_soil = soil_moisture > SOIL_MOISTURE_SATURATED
    tilt_drifting = tilt_magnitude > TILT_DRIFT_WARNING_DEG

    return heavy_rain and saturated_soil and tilt_drifting


def apply_to_sensor_csv(input_path=None, output_path=None):
    """
    Applies the dynamic risk function to every row of the sensor CSV from
    Phase 1, and flags which rows would have fired an alert. Useful both
    for a sanity check now and as sample data for the backend/frontend
    to develop against before the real live pipeline is wired up.
    """
    data_dir = _find_data_dir()
    if input_path is None:
        input_path = os.path.join(data_dir, "synthetic_sensors.csv")
    if output_path is None:
        output_path = os.path.join(data_dir, "synthetic_sensors_with_risk.csv")

    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Couldn't find {input_path}. Run generate_sensors.py first, "
            f"and make sure its output data/ folder is either next to this "
            f"script or one level up (project root)."
        )

    df = pd.read_csv(input_path)

    df["risk_score"] = df.apply(
        lambda r: calculate_dynamic_risk(
            r["Soil_Moisture"], r["Pore_Water_Pressure"],
            r["Tilt_X"], r["Tilt_Y"], r["Rainfall_24h"],
        ),
        axis=1,
    )
    df["risk_label"] = df["risk_score"].apply(risk_label_from_score)
    df["alert_fired"] = df.apply(
        lambda r: should_fire_alert(
            r["Soil_Moisture"], r["Tilt_X"], r["Tilt_Y"], r["Rainfall_24h"],
        ),
        axis=1,
    )

    df.to_csv(output_path, index=False)

    alert_count = df["alert_fired"].sum()
    print(f"Processed {len(df)} rows.")
    print(f"Alerts that would fire: {alert_count}")
    print(f"Risk label distribution:\n{df['risk_label'].value_counts()}")
    print(f"Saved: {output_path}")

    return df


if __name__ == "__main__":
    apply_to_sensor_csv()
