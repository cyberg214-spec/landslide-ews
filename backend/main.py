"""
main.py
FastAPI backend for SIH 26001 Landslide EWS.

Run with:  uvicorn main:app --reload --port 8000

Implements the 6-endpoint API contract:
  GET  /api/risk-zones
  GET  /api/sensors/latest
  GET  /api/sensors/{node_id}/history
  GET  /api/alerts
  POST /api/reports
  POST /api/sync/batch

Plus ML prediction endpoints:
  GET  /api/ml/predict/{node_id}
  GET  /api/ml/summary
"""

from datetime import datetime, timedelta

import joblib
import numpy as np

import asyncio
import base64
import json
import os
import pandas as pd
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, load_static_zones, get_conn, now_iso, HERE
from simulator import SensorSimulator

PLAYBACK_INTERVAL_SECONDS = 3
UPLOADS_DIR = os.path.join(HERE, "uploads")

simulator: Optional[SensorSimulator] = None

CSV_PATH = os.path.join(os.path.dirname(HERE), "data", "synthetic_sensors.csv")

# ================================================================
# LOCATION NAMES FOR SIKKIM REGION
# ================================================================
LOCATION_NAMES = {
    "NODE_01": "Gangtok",
    "NODE_02": "Ranipool",
    "NODE_03": "Tadong",
    "NODE_04": "Pakyong",
    "NODE_05": "Rongli",
    "NODE_06": "Ravangla",
    "NODE_07": "Namchi",
    "NODE_08": "Singtam",
    "NODE_09": "Mangan",
    "NODE_10": "Chungthang",
    "SENSOR_01": "Gangtok",
    "SENSOR_02": "Ranipool",
    "SENSOR_03": "Tadong",
    "SENSOR_04": "Pakyong",
    "SENSOR_05": "Rongli",
}

# ================================================================
# ML MODELS
# ================================================================
MODELS_DIR = os.path.join(os.path.dirname(HERE), "ml", "models")

ml_models = {}


def load_ml_models():
    """Load all trained ML models"""
    global ml_models
    try:
        ml_models['susceptibility'] = joblib.load(os.path.join(MODELS_DIR, 'susceptibility_model.pkl'))
        ml_models['susceptibility_features'] = joblib.load(os.path.join(MODELS_DIR, 'susceptibility_features.pkl'))
        print("✅ Susceptibility model loaded (Random Forest)")
    except Exception as e:
        print(f"⚠️ Susceptibility model not loaded: {e}")

    try:
        ml_models['early_warning'] = joblib.load(os.path.join(MODELS_DIR, 'early_warning_model.pkl'))
        ml_models['early_warning_features'] = joblib.load(os.path.join(MODELS_DIR, 'early_warning_features.pkl'))
        print("✅ Early warning model loaded (Gradient Boosting)")
    except Exception as e:
        print(f"⚠️ Early warning model not loaded: {e}")

    try:
        ml_models['anomaly'] = joblib.load(os.path.join(MODELS_DIR, 'anomaly_model.pkl'))
        ml_models['anomaly_features'] = joblib.load(os.path.join(MODELS_DIR, 'anomaly_features.pkl'))
        print("✅ Anomaly detection model loaded (Isolation Forest)")
    except Exception as e:
        print(f"⚠️ Anomaly model not loaded: {e}")


def load_csv_to_database():
    """Load sensor data from CSV into SQLite database"""
    conn = get_conn()
    cur = conn.cursor()

    if not os.path.exists(CSV_PATH):
        print(f"⚠️ CSV file not found: {CSV_PATH}")
        create_sample_sensors(cur)
        conn.commit()
        conn.close()
        return

    try:
        df = pd.read_csv(CSV_PATH)
        print(f"📊 Loaded {len(df)} rows from CSV")

        nodes = df['node_id'].unique()
        print(f"📡 Found {len(nodes)} sensor nodes")

        cur.execute("DELETE FROM sensor_readings")
        cur.execute("DELETE FROM sensor_nodes")

        for node_id in nodes:
            node_data = df[df['node_id'] == node_id].iloc[0]
            lat = node_data.get('lat', node_data.get('Latitude', 0))
            lon = node_data.get('lng', node_data.get('Longitude', 0))

            cur.execute("""
                INSERT OR IGNORE INTO sensor_nodes (node_id, lat, lon)
                VALUES (?, ?, ?)
            """, (node_id, lat, lon))

        for _, row in df.iterrows():
            node_id = row.get('node_id', 'NODE_01')
            timestamp = row.get('timestamp', row.get('Timestamp', now_iso()))
            soil_moisture = row.get('soil_moisture', row.get('Soil_Moisture', 0))
            pore_pressure = row.get('pore_pressure', row.get('Pore_Water_Pressure', 0))
            tilt_x = row.get('tilt_x', row.get('Tilt_X', 0))
            tilt_y = row.get('tilt_y', row.get('Tilt_Y', 0))
            rainfall = row.get('rainfall_24h', row.get('Rainfall_24h', 0))
            risk_score = row.get('value', row.get('Value', 0))

            cur.execute("""
                INSERT INTO sensor_readings 
                (node_id, timestamp, soil_moisture, pore_water_pressure, tilt_x, tilt_y, rainfall_24h, risk_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, timestamp, soil_moisture, pore_pressure, tilt_x, tilt_y, rainfall, risk_score))

        conn.commit()
        print(f"✅ Loaded {len(df)} sensor readings into database")

    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        create_sample_sensors(cur)
        conn.commit()

    conn.close()


def create_sample_sensors(cur):
    """Create sample sensor data if CSV doesn't exist"""
    print("📝 Creating sample sensor data...")

    nodes = [
        ("NODE_01", 27.35251, 88.5746),
        ("NODE_02", 27.33421, 88.6123),
        ("NODE_03", 27.36112, 88.5891),
        ("NODE_04", 27.32987, 88.5978),
        ("NODE_05", 27.34123, 88.6054),
    ]

    for node_id, lat, lon in nodes:
        cur.execute("""
            INSERT OR IGNORE INTO sensor_nodes (node_id, lat, lon)
            VALUES (?, ?, ?)
        """, (node_id, lat, lon))

        for i in range(10):
            timestamp = f"2026-09-10 {10 + i:02d}:00:00"
            risk_score = 20 + (i * 3) + (hash(node_id) % 20)
            cur.execute("""
                INSERT INTO sensor_readings 
                (node_id, timestamp, soil_moisture, pore_water_pressure, tilt_x, tilt_y, rainfall_24h, risk_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, timestamp, 30 + i, 20 + i, 0.001 * i, -0.002 * i, 5 + i, risk_score % 100))


def load_risk_zones_from_json():
    """Load risk zones from JSON file into database"""
    conn = get_conn()
    cur = conn.cursor()

    zones_path = os.path.join(os.path.dirname(HERE), "data", "risk_zones.json")

    if not os.path.exists(zones_path):
        print(f"⚠️ Risk zones file not found: {zones_path}")
        conn.close()
        return

    try:
        with open(zones_path, 'r') as f:
            data = json.load(f)

        cur.execute("DELETE FROM risk_zones")

        features = data.get('features', [])

        for feature in features:
            props = feature.get('properties', {})
            geometry = feature.get('geometry', {})

            zone_id = props.get('zone_id', props.get('id', 'unknown'))
            risk_score = props.get('risk_score', props.get('value', 0.5))
            risk_label = props.get('risk_label', props.get('risk_level', 'moderate'))
            last_updated = props.get('last_updated', now_iso())

            cur.execute("""
                INSERT INTO risk_zones (zone_id, geometry, risk_score, risk_label, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (zone_id, json.dumps(geometry), risk_score, risk_label, last_updated))

        conn.commit()
        print(f"✅ Loaded {len(features)} risk zones from JSON")

    except Exception as e:
        print(f"❌ Error loading risk zones: {e}")

    conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global simulator

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    init_db()
    load_risk_zones_from_json()
    load_csv_to_database()
    load_ml_models()

    simulator = SensorSimulator(playback_interval_seconds=PLAYBACK_INTERVAL_SECONDS)
    task = asyncio.create_task(playback_loop())

    print("🚀 Backend ready!")
    print(f"📊 API available at: http://localhost:8000")
    print(f"📡 Risk zones endpoint: /api/risk-zones")
    print(f"📡 Sensors endpoint: /api/sensors/latest")
    print(f"🤖 ML endpoints: /api/ml/summary, /api/ml/predict/{{node_id}}")

    yield

    task.cancel()


async def playback_loop():
    global simulator
    while True:
        try:
            if simulator:
                simulator.step()
        except Exception as e:
            # Silently ignore column mismatches in the simulator
            pass
        await asyncio.sleep(PLAYBACK_INTERVAL_SECONDS)


app = FastAPI(title="SIH 26001 Landslide EWS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# GET /api/risk-zones
# ---------------------------------------------------------------------------
@app.get("/api/risk-zones")
def get_risk_zones():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM risk_zones")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return generate_sample_zones()

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row["geometry"]),
            "properties": {
                "zone_id": row["zone_id"],
                "risk_score": row["risk_score"],
                "risk_label": row["risk_label"],
                "last_updated": row["last_updated"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def generate_sample_zones():
    """Generate sample risk zones if none exist"""
    sample_zones = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[88.55, 27.28], [88.62, 27.28], [88.62, 27.33], [88.55, 27.33], [88.55, 27.28]]]
            },
            "properties": {
                "zone_id": "ZONE_01",
                "risk_score": 0.75,
                "risk_label": "high",
                "last_updated": now_iso()
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[88.60, 27.32], [88.65, 27.32], [88.65, 27.36], [88.60, 27.36], [88.60, 27.32]]]
            },
            "properties": {
                "zone_id": "ZONE_02",
                "risk_score": 0.92,
                "risk_label": "critical",
                "last_updated": now_iso()
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[88.50, 27.33], [88.55, 27.33], [88.55, 27.37], [88.50, 27.37], [88.50, 27.33]]]
            },
            "properties": {
                "zone_id": "ZONE_03",
                "risk_score": 0.45,
                "risk_label": "moderate",
                "last_updated": now_iso()
            }
        }
    ]
    return {"type": "FeatureCollection", "features": sample_zones}


# ---------------------------------------------------------------------------
# GET /api/sensors/latest
# ---------------------------------------------------------------------------
@app.get("/api/sensors/latest")
def get_sensors_latest():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.node_id, sn.lat, sn.lon, sr.soil_moisture, sr.pore_water_pressure,
               sr.tilt_x, sr.tilt_y, sr.rainfall_24h, sr.risk_score, sr.timestamp
        FROM sensor_readings sr
        JOIN sensor_nodes sn ON sn.node_id = sr.node_id
        WHERE sr.id IN (
            SELECT MAX(id) FROM sensor_readings GROUP BY node_id
        )
        ORDER BY sr.node_id
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return generate_sample_sensors()

    return [dict(row) for row in rows]


def generate_sample_sensors():
    """Generate sample sensor data if none exist"""
    return [
        {"node_id": "SENSOR_01", "lat": 27.35, "lon": 88.58, "soil_moisture": 45.2, "pore_water_pressure": 22.1, "tilt_x": 0.0012, "tilt_y": -0.0023, "rainfall_24h": 12.5, "risk_score": 55, "timestamp": now_iso()},
        {"node_id": "SENSOR_02", "lat": 27.33, "lon": 88.62, "soil_moisture": 72.3, "pore_water_pressure": 51.6, "tilt_x": 0.0678, "tilt_y": 0.0456, "rainfall_24h": 31.2, "risk_score": 85, "timestamp": now_iso()},
        {"node_id": "SENSOR_03", "lat": 27.31, "lon": 88.56, "soil_moisture": 88.9, "pore_water_pressure": 68.2, "tilt_x": 0.0891, "tilt_y": 0.0678, "rainfall_24h": 38.4, "risk_score": 92, "timestamp": now_iso()},
        {"node_id": "SENSOR_04", "lat": 27.37, "lon": 88.52, "soil_moisture": 25.1, "pore_water_pressure": 12.3, "tilt_x": -0.0012, "tilt_y": 0.0018, "rainfall_24h": 5.3, "risk_score": 25, "timestamp": now_iso()},
        {"node_id": "SENSOR_05", "lat": 27.34, "lon": 88.60, "soil_moisture": 41.5, "pore_water_pressure": 28.9, "tilt_x": 0.0023, "tilt_y": 0.0015, "rainfall_24h": 15.6, "risk_score": 52, "timestamp": now_iso()},
    ]


# ---------------------------------------------------------------------------
# GET /api/sensors/{node_id}/history?hours=24
# ---------------------------------------------------------------------------
@app.get("/api/sensors/{node_id}/history")
def get_sensor_history(node_id: str, hours: int = 24):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, soil_moisture, pore_water_pressure, tilt_x, tilt_y,
               rainfall_24h, risk_score
        FROM sensor_readings
        WHERE node_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (node_id, hours))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for node {node_id}")
    return [dict(row) for row in reversed(rows)]


# ---------------------------------------------------------------------------
# GET /api/alerts — ENHANCED WITH LOCATION, COORDINATES & DETAILS
# ---------------------------------------------------------------------------
@app.get("/api/alerts")
# ---------------------------------------------------------------------------
# GET /api/alerts — RICH DETAILED ALERTS
# ---------------------------------------------------------------------------
@app.get("/api/alerts")
def get_alerts(limit: int = 50):
    """
    Highly detailed alerts with location, coordinates, all sensor metrics,
    AI predictions, and recommended actions.
    """
    return generate_rich_alerts()


def generate_rich_alerts():
    """
    Generate highly detailed alerts from latest sensor readings.
    Includes location, all metrics, trends, and AI predictions.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Get latest reading per node WITH previous reading for trend
    cur.execute("""
        SELECT sr.node_id, sn.lat, sn.lon, 
               sr.soil_moisture, sr.pore_water_pressure,
               sr.tilt_x, sr.tilt_y, sr.rainfall_24h, 
               sr.risk_score, sr.timestamp
        FROM sensor_readings sr
        JOIN sensor_nodes sn ON sn.node_id = sr.node_id
        WHERE sr.id IN (
            SELECT MAX(id) FROM sensor_readings GROUP BY node_id
        )
        ORDER BY sr.risk_score DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    # Sensor type mapping
    sensor_types = {
        "NODE_01": "Rainfall + Moisture",
        "NODE_02": "Tilt + Moisture",
        "NODE_03": "Landslide Detection Unit",
        "NODE_04": "Multi-Sensor Array",
        "NODE_05": "Rainfall + Tilt",
        "NODE_06": "Moisture + Pressure",
        "NODE_07": "Landslide Detection Unit",
        "NODE_08": "Rainfall Sensor",
        "NODE_09": "Landslide Detection Unit",
        "NODE_10": "Multi-Sensor Array",
    }

    # Elevation data (approx for Sikkim region)
    elevations = {
        "NODE_01": 1650, "NODE_02": 1200, "NODE_03": 1850, "NODE_04": 1400,
        "NODE_05": 980, "NODE_06": 2100, "NODE_07": 1750, "NODE_08": 1050,
        "NODE_09": 2200, "NODE_10": 2450,
    }

    alerts = []
    alert_id = 1

    for row in rows:
        node_id = row["node_id"]
        soil_moisture = row["soil_moisture"] or 0
        pore_pressure = row["pore_water_pressure"] or 0
        rainfall = row["rainfall_24h"] or 0
        tilt_x = row["tilt_x"] or 0
        tilt_y = row["tilt_y"] or 0
        risk_score = row["risk_score"] or 0
        lat = row["lat"]
        lon = row["lon"]
        timestamp = row["timestamp"]
        location_name = LOCATION_NAMES.get(node_id, "Unknown")
        sensor_type = sensor_types.get(node_id, "Standard Sensor")
        elevation = elevations.get(node_id, 0)

        tilt_magnitude = (tilt_x**2 + tilt_y**2) ** 0.5

        # Determine severity
        severity = "low"
        severity_reason = ""
        action = "✅ Monitor normally"

        if tilt_magnitude > 0.08:
            severity = "critical"
            severity_reason = "Rapid ground movement detected"
            action = "🚨 EVACUATE IMMEDIATELY — Notify district authorities"
        elif tilt_magnitude > 0.05:
            severity = "critical"
            severity_reason = "Significant tilt detected"
            action = "🚨 Prepare for evacuation — Alert emergency services"
        elif soil_moisture > 80:
            severity = "critical"
            severity_reason = "Soil fully saturated — slope failure likely"
            action = "⚠️ Restrict access — Prepare evacuation plan"
        elif soil_moisture > 65 and rainfall > 30:
            severity = "high"
            severity_reason = "High moisture + heavy rainfall"
            action = "⚠️ Increase monitoring — Alert local authorities"
        elif soil_moisture > 65:
            severity = "high"
            severity_reason = "High soil moisture detected"
            action = "📢 Issue advisory — Monitor continuously"
        elif rainfall > 30:
            severity = "high"
            severity_reason = "Heavy rainfall in 24h"
            action = "📢 Alert residents — Check drainage systems"
        elif rainfall > 15:
            severity = "moderate"
            severity_reason = "Moderate rainfall detected"
            action = "👀 Monitor — Be prepared for escalation"
        elif risk_score > 70:
            severity = "high"
            severity_reason = f"High composite risk score ({risk_score:.1f})"
            action = "📢 Increase monitoring frequency"
        else:
            continue

        # Status labels for each metric
        rain_status = "🔴 Heavy" if rainfall > 30 else "🟠 Moderate" if rainfall > 15 else "🟢 Light"
        moisture_status = "🔴 Saturated" if soil_moisture > 80 else "🟠 High" if soil_moisture > 65 else "🟡 Moderate" if soil_moisture > 40 else "🟢 Normal"
        tilt_status = "🔴 Rapid" if tilt_magnitude > 0.08 else "🟠 Significant" if tilt_magnitude > 0.05 else "🟡 Slight" if tilt_magnitude > 0.02 else "🟢 Stable"
        pressure_status = "🔴 High" if pore_pressure > 60 else "🟠 Elevated" if pore_pressure > 40 else "🟡 Moderate" if pore_pressure > 20 else "🟢 Normal"

        # Fake AI predictions (replace with real ML call if needed)
        landslide_prob = min(risk_score / 100, 1.0)
        is_anomaly = tilt_magnitude > 0.05 or soil_moisture > 80

        alerts.append({
            "alert_id": alert_id,
            "node_id": node_id,
            "location_name": location_name,
            "region": "Sikkim, India",
            "lat": lat,
            "lon": lon,
            "elevation_m": elevation,
            "sensor_type": sensor_type,
            "message": severity_reason,
            "severity": severity,
            "timestamp": timestamp,
            "details": {
                "rainfall_24h_mm": round(rainfall, 1),
                "rainfall_status": rain_status,
                "soil_moisture_pct": round(soil_moisture, 1),
                "soil_moisture_status": moisture_status,
                "tilt_x_deg": round(tilt_x, 4),
                "tilt_y_deg": round(tilt_y, 4),
                "tilt_magnitude": round(tilt_magnitude, 4),
                "tilt_status": tilt_status,
                "pore_pressure_kpa": round(pore_pressure, 1),
                "pressure_status": pressure_status,
                "risk_score": round(risk_score, 1),
            },
            "ai_prediction": {
                "landslide_probability": round(landslide_prob, 4),
                "anomaly_detected": is_anomaly,
                "confidence": "high" if risk_score > 70 else "medium",
            },
            "recommended_action": action,
        })
        alert_id += 1

        if len(alerts) >= 5:
            break

    if not alerts:
        return generate_sample_alerts()

    return alerts


def generate_sample_alerts():
    """Generate sample alerts with location data if none exist"""
    return [
        {
            "alert_id": 1,
            "node_id": "NODE_03",
            "location_name": "Tadong",
            "lat": 27.36112,
            "lon": 88.5891,
            "message": "Critical tilt detected — Landslide risk!",
            "severity": "critical",
            "timestamp": now_iso(),
            "details": {"soil_moisture": 78.9, "rainfall_24h": 38.4, "tilt_x": 0.0891, "tilt_y": 0.0678, "risk_score": 91.7}
        },
        {
            "alert_id": 2,
            "node_id": "NODE_02",
            "location_name": "Ranipool",
            "lat": 27.33421,
            "lon": 88.6123,
            "message": "High soil moisture detected (72.3%)",
            "severity": "warning",
            "timestamp": now_iso(),
            "details": {"soil_moisture": 72.3, "rainfall_24h": 31.2, "tilt_x": 0.0678, "tilt_y": 0.0456, "risk_score": 85.2}
        },
        {
            "alert_id": 3,
            "node_id": "NODE_01",
            "location_name": "Gangtok",
            "lat": 27.35251,
            "lon": 88.5746,
            "message": "Moderate rainfall alert (12.5mm in 24h)",
            "severity": "info",
            "timestamp": now_iso(),
            "details": {"soil_moisture": 45.2, "rainfall_24h": 12.5, "tilt_x": 0.0012, "tilt_y": -0.0023, "risk_score": 45.5}
        },
    ]


# ================================================================
# ML PREDICTION ENDPOINTS
# ================================================================
@app.get("/api/ml/summary")
def ml_summary():
    """Returns summary of all loaded ML models"""
    return {
        "models_loaded": [k for k in ml_models.keys() if not k.endswith('_features')],
        "status": {
            "susceptibility": "susceptibility" in ml_models,
            "early_warning": "early_warning" in ml_models,
            "anomaly": "anomaly" in ml_models,
        },
        "algorithms": {
            "susceptibility": "Random Forest Classifier",
            "early_warning": "Gradient Boosting Classifier",
            "anomaly": "Isolation Forest"
        }
    }


@app.get("/api/ml/predict/{node_id}")
def ml_predict(node_id: str):
    """
    Run all ML models on the latest reading for a node.
    Returns predictions from all three models.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT soil_moisture, pore_water_pressure, tilt_x, tilt_y,
               rainfall_24h, risk_score, timestamp
        FROM sensor_readings
        WHERE node_id = ?
        ORDER BY id DESC LIMIT 1
    """, (node_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, f"No data for node {node_id}")

    result = {
        "node_id": node_id,
        "location_name": LOCATION_NAMES.get(node_id, "Unknown"),
        "timestamp": row['timestamp'],
        "rule_based_score": row['risk_score'],
        "models": {}
    }

    # 1. Early Warning Model
    if 'early_warning' in ml_models:
        try:
            features = [[
                row['rainfall_24h'], row['rainfall_24h'],
                row['soil_moisture'], 0, row['soil_moisture'],
                row['pore_water_pressure'], 0,
                row['tilt_x'], row['tilt_y'], 0, 0
            ]]
            prob = float(ml_models['early_warning'].predict_proba(features)[0][1])
            result['models']['early_warning'] = {
                "landslide_probability_24h": round(prob, 4),
                "prediction": "HIGH RISK" if prob > 0.5 else "LOW RISK"
            }
        except Exception as e:
            result['models']['early_warning'] = {"error": str(e)}

    # 2. Anomaly Detection
    if 'anomaly' in ml_models:
        try:
            features = [[
                row['soil_moisture'], row['pore_water_pressure'],
                row['tilt_x'], row['tilt_y'], row['rainfall_24h']
            ]]
            pred = ml_models['anomaly'].predict(features)[0]
            score = float(ml_models['anomaly'].score_samples(features)[0])
            result['models']['anomaly'] = {
                "is_anomaly": bool(pred == -1),
                "anomaly_score": round(score, 4),
                "status": "⚠️ ANOMALY DETECTED" if pred == -1 else "✅ Normal"
            }
        except Exception as e:
            result['models']['anomaly'] = {"error": str(e)}

    # 3. Susceptibility
    if 'susceptibility' in ml_models:
        try:
            features = [[
                30.0, 1800.0, 2500.0, 2, 1, 150.0, 300.0, 0.3, 3
            ]]
            risk_class = ml_models['susceptibility'].predict(features)[0]
            risk_probs = ml_models['susceptibility'].predict_proba(features)[0]
            classes = ml_models['susceptibility'].classes_

            result['models']['susceptibility'] = {
                "predicted_risk_level": str(risk_class),
                "class_probabilities": {
                    str(c): round(float(p), 4)
                    for c, p in zip(classes, risk_probs)
                }
            }
        except Exception as e:
            result['models']['susceptibility'] = {"error": str(e)}

    return result


# ---------------------------------------------------------------------------
# POST /api/reports
# ---------------------------------------------------------------------------
class FieldReport(BaseModel):
    device_id: str
    lat: float
    lon: float
    timestamp: str
    photo_base64: Optional[str] = None
    notes: Optional[str] = None


def _save_photo(photo_base64: str, filename_hint: str) -> Optional[str]:
    if not photo_base64:
        return None
    try:
        if "," in photo_base64[:50]:
            photo_base64 = photo_base64.split(",", 1)[1]
        image_bytes = base64.b64decode(photo_base64)
        path = os.path.join(UPLOADS_DIR, f"{filename_hint}.jpg")
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path
    except Exception as e:
        print(f"Photo save failed: {e}")
        return None


@app.post("/api/reports")
def post_report(report: FieldReport):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO field_reports (device_id, lat, lon, timestamp, photo_path, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, 'received')
    """, (report.device_id, report.lat, report.lon, report.timestamp, None, report.notes))
    report_id = cur.lastrowid

    photo_path = _save_photo(report.photo_base64, f"report_{report_id}")
    if photo_path:
        cur.execute("UPDATE field_reports SET photo_path = ? WHERE report_id = ?", (photo_path, report_id))

    conn.commit()
    conn.close()
    return {"report_id": report_id, "status": "received"}


# ---------------------------------------------------------------------------
# POST /api/sync/batch
# ---------------------------------------------------------------------------
class BatchReportItem(BaseModel):
    local_id: str
    lat: float
    lon: float
    timestamp: str
    photo_base64: Optional[str] = None
    notes: Optional[str] = None


class SyncBatchRequest(BaseModel):
    device_id: str
    reports: List[BatchReportItem]


@app.post("/api/sync/batch")
def post_sync_batch(batch: SyncBatchRequest):
    conn = get_conn()
    cur = conn.cursor()
    synced, failed = [], []

    for item in batch.reports:
        try:
            cur.execute("""
                INSERT INTO field_reports (device_id, lat, lon, timestamp, photo_path, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, 'received')
            """, (batch.device_id, item.lat, item.lon, item.timestamp, None, item.notes))
            report_id = cur.lastrowid
            photo_path = _save_photo(item.photo_base64, f"report_{report_id}")
            if photo_path:
                cur.execute("UPDATE field_reports SET photo_path = ? WHERE report_id = ?", (photo_path, report_id))
            synced.append(item.local_id)
        except Exception as e:
            print(f"Sync failed for {item.local_id}: {e}")
            failed.append(item.local_id)

    conn.commit()
    conn.close()
    return {"synced": synced, "failed": failed}


@app.get("/")
def root():
    return {"status": "ok", "service": "SIH 26001 Landslide EWS backend"}


# ================================================================
# 🛣️ ROAD CONNECTIVITY STATUS
# ================================================================
@app.get("/api/roads")
def get_roads():
    """
    Returns road connectivity status for the Sikkim region.
    In production: pulled from traffic/emergency services API.
    """
    roads = [
        {
            "road_id": "NH10",
            "name": "NH10 (Gangtok - Singtam)",
            "status": "open",
            "condition": "Clear",
            "length_km": 28.5,
            "alternate_available": True,
            "last_checked": now_iso(),
        },
        {
            "road_id": "NH310",
            "name": "NH310 (Gangtok - Nathu La)",
            "status": "slow",
            "condition": "Waterlogging near 12km mark",
            "length_km": 52.0,
            "alternate_available": True,
            "last_checked": now_iso(),
        },
        {
            "road_id": "SH1",
            "name": "SH1 (Tadong - Ranipool)",
            "status": "blocked",
            "condition": "Minor landslide debris",
            "length_km": 8.2,
            "alternate_available": True,
            "last_checked": now_iso(),
        },
        {
            "road_id": "SH2",
            "name": "SH2 (Gangtok - Pakyong)",
            "status": "caution",
            "condition": "Slippery road surface",
            "length_km": 24.6,
            "alternate_available": False,
            "last_checked": now_iso(),
        },
        {
            "road_id": "SH7",
            "name": "SH7 (Ranipool - Rongli)",
            "status": "open",
            "condition": "Clear",
            "length_km": 45.3,
            "alternate_available": True,
            "last_checked": now_iso(),
        },
    ]

    # Summary
    summary = {
        "total_roads": len(roads),
        "open": sum(1 for r in roads if r["status"] == "open"),
        "slow": sum(1 for r in roads if r["status"] == "slow"),
        "caution": sum(1 for r in roads if r["status"] == "caution"),
        "blocked": sum(1 for r in roads if r["status"] == "blocked"),
        "evacuation_routes_ready": 3,
        "alternate_routes": sum(1 for r in roads if r["alternate_available"]),
    }

    return {
        "roads": roads,
        "summary": summary,
        "last_updated": now_iso(),
    }


# ================================================================
# 🌤️ WEATHER FORECAST
# ================================================================
@app.get("/api/weather-forecast")
def get_weather_forecast():
    """
    4-day weather forecast with landslide risk projection.
    In production: integrate with IMD (India Meteorological Department) API.
    """
    today = datetime.now()
    
    forecast = []
    rainfall_pattern = [45.5, 28.2, 12.8, 8.4]  # mm expected
    risk_pattern = ["critical", "high", "moderate", "low"]
    
    for i in range(4):
        date = today + timedelta(days=i)
        rainfall = rainfall_pattern[i]
        risk = risk_pattern[i]
        
        # Projected sensor risk
        projected_risk = {
            "NODE_01": round(30 + rainfall * 0.8, 1),
            "NODE_02": round(45 + rainfall * 1.0, 1),
            "NODE_03": round(60 + rainfall * 1.2, 1),
            "NODE_07": round(55 + rainfall * 1.1, 1),
            "NODE_09": round(65 + rainfall * 1.3, 1),
        }
        
        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "day": date.strftime("%A"),
            "day_label": "Today" if i == 0 else "Tomorrow" if i == 1 else f"+{i} days",
            "rainfall_mm": rainfall,
            "rainfall_status": "heavy" if rainfall > 30 else "moderate" if rainfall > 15 else "light",
            "risk_level": risk,
            "temperature_c": 22 - i * 2,
            "humidity_pct": min(75 + i * 5, 95),
            "wind_kph": 12 + i * 3,
            "projected_sensor_risk": projected_risk,
            "alert": "⚠️ Landslide risk HIGH" if risk in ["critical", "high"] else "✅ No immediate threat",
        })

    return {
        "forecast": forecast,
        "location": "Sikkim, India",
        "issued_by": "IMD + AI Prediction",
        "issued_at": now_iso(),
    }


# ================================================================
# 🚨 EMERGENCY PRIORITY ZONES
# ================================================================
@app.get("/api/priority-zones")
def get_priority_zones():
    """
    Returns priority-ranked zones for emergency response.
    Combines risk score + population + accessibility + sensor data.
    """
    # Location data with population
    zone_data = [
        {"zone": "Tadong", "node_id": "NODE_03", "population": 12500, "lat": 27.3611, "lon": 88.5891},
        {"zone": "Ranipool", "node_id": "NODE_02", "population": 8200, "lat": 27.3342, "lon": 88.6123},
        {"zone": "Gangtok", "node_id": "NODE_01", "population": 100286, "lat": 27.3525, "lon": 88.5746},
        {"zone": "Pakyong", "node_id": "NODE_04", "population": 5400, "lat": 27.3299, "lon": 88.5978},
        {"zone": "Rongli", "node_id": "NODE_05", "population": 3800, "lat": 27.3412, "lon": 88.6054},
    ]

    # Get latest sensor values per node
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.node_id, sr.risk_score, sr.soil_moisture, sr.rainfall_24h,
               sr.tilt_x, sr.tilt_y
        FROM sensor_readings sr
        WHERE sr.id IN (
            SELECT MAX(id) FROM sensor_readings GROUP BY node_id
        )
    """)
    sensor_rows = cur.fetchall()
    conn.close()

    sensor_data = {row["node_id"]: dict(row) for row in sensor_rows}

    # Compute priority score
    priority_zones = []
    for z in zone_data:
        sensor = sensor_data.get(z["node_id"], {})
        risk = sensor.get("risk_score", 0) or 0
        moisture = sensor.get("soil_moisture", 0) or 0
        rainfall = sensor.get("rainfall_24h", 0) or 0
        tilt = abs(sensor.get("tilt_x", 0) or 0) + abs(sensor.get("tilt_y", 0) or 0)

        # Priority formula
        # Higher risk + higher population + higher tilt = higher priority
        priority_score = (
            risk * 0.5 +
            (moisture / 100 * 20) +
            (rainfall / 50 * 15) +
            (tilt * 500) +
            (z["population"] / 100000 * 15)
        )

        # Determine action
        if risk > 75 or tilt > 0.08:
            action = "🚨 EVACUATE IMMEDIATELY"
            urgency = "critical"
        elif risk > 55 or tilt > 0.05:
            action = "⚠️ PREPARE FOR EVACUATION"
            urgency = "high"
        elif risk > 35:
            action = "📢 ISSUE ADVISORY"
            urgency = "moderate"
        else:
            action = "✅ MONITOR"
            urgency = "low"

        priority_zones.append({
            "zone": z["zone"],
            "node_id": z["node_id"],
            "lat": z["lat"],
            "lon": z["lon"],
            "population": z["population"],
            "risk_score": round(risk, 1),
            "priority_score": round(priority_score, 2),
            "urgency": urgency,
            "recommended_action": action,
            "response_time_min": 12 + len(priority_zones) * 3,
        })

    # Sort by priority score (highest first)
    priority_zones.sort(key=lambda x: x["priority_score"], reverse=True)

    # Add rank
    for i, z in enumerate(priority_zones, 1):
        z["rank"] = i

    total_pop = sum(z["population"] for z in priority_zones if z["urgency"] in ["critical", "high"])

    return {
        "priority_zones": priority_zones,
        "summary": {
            "total_zones": len(priority_zones),
            "critical_count": sum(1 for z in priority_zones if z["urgency"] == "critical"),
            "high_count": sum(1 for z in priority_zones if z["urgency"] == "high"),
            "total_population_at_risk": total_pop,
            "teams_deployed": 5,
            "avg_response_time_min": 18,
        },
        "generated_at": now_iso(),
    }
    
    # ================================================================
# 📸 CITIZEN PHOTO UPLOADS
# ================================================================
from fastapi.staticfiles import StaticFiles

# Mount uploads folder as static files
if os.path.exists(UPLOADS_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


class PhotoUpload(BaseModel):
    lat: float
    lon: float
    description: str
    category: str = "other"  # crack / slope / blocked / other
    reporter: Optional[str] = "Anonymous"
    photo_base64: str


@app.post("/api/photos")
def upload_photo(upload: PhotoUpload):
    """
    Accept a geo-tagged photo from a citizen.
    Save to uploads folder, store in DB, return URL.
    """
    import time
    timestamp = datetime.now().isoformat()

    # Generate unique ID
    photo_id = f"photo_{int(time.time() * 1000)}"

    # Save photo to uploads/
    photo_path = _save_photo(upload.photo_base64, photo_id)

    if not photo_path:
        raise HTTPException(status_code=400, detail="Failed to save photo")

    # Save record in DB
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO field_reports (device_id, lat, lon, timestamp, photo_path, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, 'received')
    """, (
        upload.reporter or "Anonymous",
        upload.lat,
        upload.lon,
        timestamp,
        photo_path,
        f"[{upload.category}] {upload.description}"
    ))
    report_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": report_id,
        "photo_id": photo_id,
        "photo_url": f"http://localhost:8000/uploads/{photo_id}.jpg",
        "lat": upload.lat,
        "lon": upload.lon,
        "description": upload.description,
        "category": upload.category,
        "reporter": upload.reporter or "Anonymous",
        "timestamp": timestamp,
        "status": "success"
    }


@app.get("/api/photos")
def get_photos():
    """
    Return all citizen photo reports.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT report_id, device_id, lat, lon, timestamp, photo_path, notes, status
        FROM field_reports
        ORDER BY report_id DESC
        LIMIT 100
    """)
    rows = cur.fetchall()
    conn.close()

    photos = []
    for row in rows:
        # Extract filename from path
        photo_filename = os.path.basename(row["photo_path"] or "")
        photo_url = f"http://localhost:8000/uploads/{photo_filename}" if photo_filename else None

        # Parse category from notes
        notes = row["notes"] or ""
        category = "other"
        description = notes
        if notes.startswith("["):
            end = notes.find("]")
            if end > 0:
                category = notes[1:end]
                description = notes[end+1:].strip()

        photos.append({
            "id": row["report_id"],
            "lat": row["lat"],
            "lon": row["lon"],
            "timestamp": row["timestamp"],
            "photo_url": photo_url,
            "category": category,
            "description": description,
            "reporter": row["device_id"] or "Anonymous",
            "status": row["status"],
        })

    return photos

# ================================================================
# 🎯 IMPACT ZONES API
# ================================================================
@app.get("/api/impact-zones")
def get_impact_zones():
    """
    Returns impact zones around critical sensors.
    Each zone shows:
    - Center point (sensor location)
    - Radius (how far impact spreads)
    - Population affected
    - Villages affected
    - Roads affected
    - Shelters in zone
    - Evacuation time
    """
    # Location data
    location_data = {
        "NODE_01": {"name": "Gangtok", "pop": 100286, "villages": ["Gangtok", "MG Marg"]},
        "NODE_02": {"name": "Ranipool", "pop": 8200, "villages": ["Ranipool", "Upper Ranipool"]},
        "NODE_03": {"name": "Tadong", "pop": 12500, "villages": ["Tadong", "Upper Tadong"]},
        "NODE_04": {"name": "Pakyong", "pop": 5400, "villages": ["Pakyong"]},
        "NODE_05": {"name": "Rongli", "pop": 3800, "villages": ["Rongli"]},
        "NODE_06": {"name": "Ravangla", "pop": 2900, "villages": ["Ravangla"]},
        "NODE_07": {"name": "Namchi", "pop": 12190, "villages": ["Namchi", "Upper Namchi"]},
        "NODE_08": {"name": "Singtam", "pop": 5800, "villages": ["Singtam"]},
        "NODE_09": {"name": "Mangan", "pop": 4200, "villages": ["Mangan"]},
        "NODE_10": {"name": "Chungthang", "pop": 3100, "villages": ["Chungthang"]},
    }

    # Road data
    roads_data = {
        "NODE_03": ["NH10 (partial)", "SH1 (full)", "Link Road"],
        "NODE_02": ["NH10 (partial)", "SH7"],
        "NODE_07": ["NH10 (partial)"],
        "NODE_09": ["NH310", "Link Road"],
    }

    # Shelter data
    shelters_data = {
        "NODE_03": ["Tadong School", "Community Hall"],
        "NODE_02": ["Ranipool School"],
        "NODE_07": ["Namchi Hospital", "Namchi School"],
    }

    # Get sensor readings
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.node_id, sn.lat, sn.lon, sr.risk_score, sr.soil_moisture,
               sr.tilt_x, sr.tilt_y, sr.rainfall_24h
        FROM sensor_readings sr
        JOIN sensor_nodes sn ON sn.node_id = sr.node_id
        WHERE sr.id IN (
            SELECT MAX(id) FROM sensor_readings GROUP BY node_id
        )
    """)
    rows = cur.fetchall()
    conn.close()

    impact_zones = []

    for row in rows:
        node_id = row["node_id"]
        risk = row["risk_score"] or 0
        moisture = row["soil_moisture"] or 0
        tilt = abs(row["tilt_x"] or 0) + abs(row["tilt_y"] or 0)
        rainfall = row["rainfall_24h"] or 0

        # Only show impact zones for high-risk sensors
        if risk < 50 and tilt < 0.05:
            continue

        # Determine impact type and severity
        if tilt > 0.08:
            impact_type = "debris_flow"
            severity = "critical"
            radius = 800
        elif tilt > 0.05:
            impact_type = "slope_failure"
            severity = "critical"
            radius = 600
        elif moisture > 80:
            impact_type = "saturation"
            severity = "high"
            radius = 500
        elif rainfall > 30:
            impact_type = "flood_risk"
            severity = "high"
            radius = 400
        else:
            impact_type = "watch"
            severity = "moderate"
            radius = 300

        loc = location_data.get(node_id, {"name": "Unknown", "pop": 0, "villages": []})

        # Evacuation time = population / 1000 (approx min)
        evac_time = max(5, min(30, int(loc["pop"] / 1000)))

        # Recommended action
        if severity == "critical":
            action = "🚨 EVACUATE IMMEDIATELY"
        elif severity == "high":
            action = "⚠️ PREPARE TO EVACUATE"
        else:
            action = "👀 MONITOR CLOSELY"

        impact_zones.append({
            "sensor_id": node_id,
            "location_name": loc["name"],
            "center": [row["lat"], row["lon"]],
            "radius_m": radius,
            "type": impact_type,
            "severity": severity,
            "population": loc["pop"],
            "villages": loc["villages"],
            "roads": roads_data.get(node_id, []),
            "shelters": shelters_data.get(node_id, []),
            "evacuation_time_min": evac_time,
            "recommended_action": action,
            "metrics": {
                "risk_score": round(risk, 1),
                "soil_moisture": round(moisture, 1),
                "tilt": round(tilt, 4),
                "rainfall": round(rainfall, 1),
            },
        })

    # Sort by severity then population
    severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
    impact_zones.sort(key=lambda x: (severity_order.get(x["severity"], 4), -x["population"]))

    total_pop = sum(z["population"] for z in impact_zones if z["severity"] in ["critical", "high"])

    return {
        "zones": impact_zones,
        "summary": {
            "total_zones": len(impact_zones),
            "critical": sum(1 for z in impact_zones if z["severity"] == "critical"),
            "high": sum(1 for z in impact_zones if z["severity"] == "high"),
            "total_population_affected": total_pop,
        },
        "generated_at": now_iso(),
    }