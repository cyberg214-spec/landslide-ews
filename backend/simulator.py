"""
simulator.py
Replays the synthetic sensor CSV (from ml/generate_sensors.py) on a timer,
computing live risk per node and combining it with each zone's static
susceptibility to produce the "critical" escalation your demo needs.

This stands in for a real live sensor feed / message queue — the API
contract (what the frontend/mobile consume) is identical either way.
"""

import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Import the dynamic risk logic from ml/ without duplicating it
sys.path.insert(0, os.path.join(PROJECT_ROOT, "ml"))
from dynamic_risk import calculate_dynamic_risk, risk_label_from_score  # noqa: E402

from database import get_conn, now_iso  # noqa: E402

# Same bounding-box grid as ml/train_susceptibility.py — duplicated here
# deliberately (small, stable constant) rather than importing that whole
# module, so the backend doesn't need xgboost/sklearn installed.
LAT_RANGE = (27.28, 27.38)
LON_RANGE = (88.55, 88.68)
N_LAT_SPLITS = 2
N_LON_SPLITS = 2

ALERT_THRESHOLD = 0.75
ALERT_COOLDOWN_SECONDS = 60  # don't spam repeat alerts for the same zone


def assign_zone(lat, lon):
    lat_edges = [LAT_RANGE[0] + i * (LAT_RANGE[1] - LAT_RANGE[0]) / N_LAT_SPLITS for i in range(N_LAT_SPLITS + 1)]
    lon_edges = [LON_RANGE[0] + j * (LON_RANGE[1] - LON_RANGE[0]) / N_LON_SPLITS for j in range(N_LON_SPLITS + 1)]

    lat_idx = min(max(0, int((lat - LAT_RANGE[0]) / (LAT_RANGE[1] - LAT_RANGE[0]) * N_LAT_SPLITS)), N_LAT_SPLITS - 1)
    lon_idx = min(max(0, int((lon - LON_RANGE[0]) / (LON_RANGE[1] - LON_RANGE[0]) * N_LON_SPLITS)), N_LON_SPLITS - 1)
    zone_num = lat_idx * N_LON_SPLITS + lon_idx + 1
    return f"ZONE_{zone_num:02d}"


class SensorSimulator:
    def __init__(self, csv_path=None, playback_interval_seconds=3):
        self.csv_path = csv_path or os.path.join(DATA_DIR, "synthetic_sensors.csv")
        self.playback_interval = playback_interval_seconds
        self._last_alert_time = {}  # zone_id -> unix timestamp

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"Couldn't find {self.csv_path}. Run ml/generate_sensors.py first "
                f"and make sure data/ is at the project root."
            )

        df = pd.read_csv(self.csv_path)
        self.timestamps = sorted(df["timestamp"].unique())
        self.df = df
        self.current_index = 0

        # Register static node lat/lon once
        conn = get_conn()
        cur = conn.cursor()
        for _, row in df.drop_duplicates("Node_ID").iterrows():
            cur.execute("""
                INSERT OR REPLACE INTO sensor_nodes (Node_ID, lat, lon) VALUES (?, ?, ?)
            """, (row["Node_ID"], row["Latitude"], row["Longitude"]))
        conn.commit()
        conn.close()

    def step(self):
        """Processes one timestamp's worth of readings (all nodes). Returns False when the CSV is exhausted (loops back to start)."""
        if self.current_index >= len(self.timestamps):
            self.current_index = 0  # loop the demo data indefinitely

        ts = self.timestamps[self.current_index]
        rows = self.df[self.df["timestamp"] == ts]

        conn = get_conn()
        cur = conn.cursor()

        zone_dynamic_max = {}  # zone_id -> max dynamic risk seen this tick

        for _, row in rows.iterrows():
            risk_score = calculate_dynamic_risk(
                row["Soil_Moisture"], row["Pore_Water_Pressure"],
                row["Tilt_X"], row["Tilt_Y"], row["Rainfall_24h"],
            )
            risk_label = risk_label_from_score(risk_score)

            cur.execute("""
                INSERT INTO sensor_readings
                    (Node_ID, timestamp, soil_moisture, pore_water_pressure,
                     tilt_x, tilt_y, rainfall_24h, risk_score, risk_label)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["Node_ID"], ts, row["Soil_Moisture"], row["Pore_Water_Pressure"],
                row["Tilt_X"], row["Tilt_Y"], row["Rainfall_24h"], risk_score, risk_label,
            ))

            zone_id = assign_zone(row["Latitude"], row["Longitude"])
            zone_dynamic_max[zone_id] = max(zone_dynamic_max.get(zone_id, 0.0), risk_score)

        # Combine each affected zone's static susceptibility with the live dynamic risk.
        # Weighted toward the live signal (0.6) since that's what should drive escalation.
        for zone_id, dynamic_score in zone_dynamic_max.items():
            cur.execute("SELECT risk_score FROM risk_zones WHERE zone_id = ?", (zone_id,))
            row = cur.fetchone()
            if row is None:
                continue
            static_score = row["risk_score"]
            combined = min(1.0, 0.4 * static_score + 0.6 * dynamic_score)
            combined_label = risk_label_from_score(combined)

            cur.execute("""
                UPDATE risk_zones SET risk_score = ?, risk_label = ?, last_updated = ?
                WHERE zone_id = ?
            """, (combined, combined_label, now_iso(), zone_id))

            if combined >= ALERT_THRESHOLD:
                last_fired = self._last_alert_time.get(zone_id, 0)
                if time.time() - last_fired > ALERT_COOLDOWN_SECONDS:
                    cur.execute("""
                        INSERT INTO alerts (zone_id, severity, message, timestamp, lat, lon)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        zone_id, combined_label,
                        f"{zone_id} risk escalated to {combined_label} ({combined:.2f})",
                        now_iso(), None, None,
                    ))
                    self._last_alert_time[zone_id] = time.time()

        conn.commit()
        conn.close()

        self.current_index += 1
        return True
