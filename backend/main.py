"""
main.py
FastAPI backend for SIH 26001 Landslide EWS.

Run with:  uvicorn main:app --reload --port 8000
"""

from datetime import datetime, timedelta

import joblib
import asyncio
import base64
import csv
import json
import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    "NODE_01": "Gangtok", "NODE_02": "Ranipool", "NODE_03": "Tadong",
    "NODE_04": "Pakyong", "NODE_05": "Rongli", "NODE_06": "Ravangla",
    "NODE_07": "Namchi", "NODE_08": "Singtam", "NODE_09": "Mangan",
    "NODE_10": "Chungthang",
    "SENSOR_01": "Gangtok", "SENSOR_02": "Ranipool", "SENSOR_03": "Tadong",
    "SENSOR_04": "Pakyong", "SENSOR_05": "Rongli",
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
    """Load sensor data from CSV into SQLite database (no pandas needed)"""
    conn = get_conn()
    cur = conn.cursor()

    if not os.path.exists(CSV_PATH):
        print(f"⚠️ CSV file not found: {CSV_PATH}")
        create_sample_sensors(cur)
        conn.commit()
        conn.close()
        return

    try:
        rows = []
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        print(f"📊 Loaded {len(rows)} rows from CSV")

        # Get unique nodes
        node_ids = list(set(r.get('node_id', '') for r in rows))
        print(f"📡 Found {len(node_ids)} sensor nodes")

        # Clear existing data
        cur.execute("DELETE FROM sensor_readings")
        cur.execute("DELETE FROM sensor_nodes")

        # Insert sensor nodes
        inserted_nodes = set()
        for row in rows:
            node_id = row.get('node_id', 'NODE_01')
            if node_id in inserted_nodes:
                continue
            try:
                lat = float(row.get('lat', 0) or 0)
                lon = float(row.get('lng', 0) or 0)
            except (ValueError, TypeError):
                lat, lon = 0, 0
            cur.execute("""
                INSERT OR IGNORE INTO sensor_nodes (node_id, lat, lon)
                VALUES (?, ?, ?)
            """, (node_id, lat, lon))
            inserted_nodes.add(node_id)

        # Insert sensor readings
        for row in rows:
            node_id = row.get('node_id', 'NODE_01')
            timestamp = row.get('timestamp', now_iso())

            try:
                soil_moisture = float(row.get('soil_moisture', 0) or 0)
                pore_pressure = float(row.get('pore_pressure', 0) or 0)
                tilt_x = float(row.get('tilt_x', 0) or 0)
                tilt_y = float(row.get('tilt_y', 0) or 0)
                rainfall = float(row.get('rainfall_24h', 0) or 0)
                risk_score = float(row.get('value', 0) or 0)
            except (ValueError, TypeError):
                continue

            cur.execute("""
                INSERT INTO sensor_readings 
                (node_id, timestamp, soil_moisture, pore_water_pressure, tilt_x, tilt_y, rainfall_24h, risk_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, timestamp, soil_moisture, pore_pressure, tilt_x, tilt_y, rainfall, risk_score))

        conn.commit()
        print(f"✅ Loaded {len(rows)} sensor readings into database")

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

    yield

    task.cancel()


async def playback_loop():
    global simulator
    while True:
        try:
            if simulator:
                simulator.step()
        except Exception:
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
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[88.55, 27.28], [88.62, 27.28], [88.62, 27.33], [88.55, 27.33], [88.55, 27.28]]]}, "properties": {"zone_id": "ZONE_01", "risk_score": 0.75, "risk_label": "high", "last_updated": now_iso()}},
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[88.60, 27.32], [88.65, 27.32], [88.65, 27.36], [88.60, 27.36], [88.60, 27.32]]]}, "properties": {"zone_id": "ZONE_02", "risk_score": 0.92, "risk_label": "critical", "last_updated": now_iso()}},
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[88.50, 27.33], [88.55, 27.33], [88.55, 27.37], [88.50, 27.37], [88.50, 27.33]]]}, "properties": {"zone_id": "ZONE_03", "risk_score": 0.45, "risk_label": "moderate", "last_updated": now_iso()}},
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
        WHERE sr.id IN (SELECT MAX(id) FROM sensor_readings GROUP BY node_id)
        ORDER BY sr.node_id
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return generate_sample_sensors()

    return [dict(row) for row in rows]


def generate_sample_sensors():
    return [
        {"node_id": "SENSOR_01", "lat": 27.35, "lon": 88.58, "soil_moisture": 45.2, "pore_water_pressure": 22.1, "tilt_x": 0.0012, "tilt_y": -0.0023, "rainfall_24h": 12.5, "risk_score": 55, "timestamp": now_iso()},
        {"node_id": "SENSOR_02", "lat": 27.33, "lon": 88.62, "soil_moisture": 72.3, "pore_water_pressure": 51.6, "tilt_x": 0.0678, "tilt_y": 0.0456, "rainfall_24h": 31.2, "risk_score": 85, "timestamp": now_iso()},
        {"node_id": "SENSOR_03", "lat": 27.31, "lon": 88.56, "soil_moisture": 88.9, "pore_water_pressure": 68.2, "tilt_x": 0.0891, "tilt_y": 0.0678, "rainfall_24h": 38.4, "risk_score": 92, "timestamp": now_iso()},
        {"node_id": "SENSOR_04", "lat": 27.37, "lon": 88.52, "soil_moisture": 25.1, "pore_water_pressure": 12.3, "tilt_x": -0.0012, "tilt_y": 0.0018, "rainfall_24h": 5.3, "risk_score": 25, "timestamp": now_iso()},
        {"node_id": "SENSOR_05", "lat": 27.34, "lon": 88.60, "soil_moisture": 41.5, "pore_water_pressure": 28.9, "tilt_x": 0.0023, "tilt_y": 0.0015, "rainfall_24h": 15.6, "risk_score": 52, "timestamp": now_iso()},
    ]


# ---------------------------------------------------------------------------
# GET /api/sensors/{node_id}/history
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
        ORDER BY id DESC LIMIT ?
    """, (node_id, hours))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No data for node {node_id}")
    return [dict(row) for row in reversed(rows)]


# ---------------------------------------------------------------------------
# GET /api/alerts
# ---------------------------------------------------------------------------
@app.get("/api/alerts")
def get_alerts(limit: int = 50):
    return generate_rich_alerts()


def generate_rich_alerts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT sr.node_id, sn.lat, sn.lon, 
               sr.soil_moisture, sr.pore_water_pressure,
               sr.tilt_x, sr.tilt_y, sr.rainfall_24h, 
               sr.risk_score, sr.timestamp
        FROM sensor_readings sr
        JOIN sensor_nodes sn ON sn.node_id = sr.node_id
        WHERE sr.id IN (SELECT MAX(id) FROM sensor_readings GROUP BY node_id)
        ORDER BY sr.risk_score DESC LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    sensor_types = {
        "NODE_01": "Rainfall + Moisture", "NODE_02": "Tilt + Moisture",
        "NODE_03": "Landslide Detection Unit", "NODE_04": "Multi-Sensor Array",
        "NODE_05": "Rainfall + Tilt", "NODE_06": "Moisture + Pressure",
        "NODE_07": "Landslide Detection Unit", "NODE_08": "Rainfall Sensor",
        "NODE_09": "Landslide Detection Unit", "NODE_10": "Multi-Sensor Array",
    }
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

        rain_status = "🔴 Heavy" if rainfall > 30 else "🟠 Moderate" if rainfall > 15 else "🟢 Light"
        moisture_status = "🔴 Saturated" if soil_moisture > 80 else "🟠 High" if soil_moisture > 65 else "🟡 Moderate" if soil_moisture > 40 else "🟢 Normal"
        tilt_status = "🔴 Rapid" if tilt_magnitude > 0.08 else "🟠 Significant" if tilt_magnitude > 0.05 else "🟡 Slight" if tilt_magnitude > 0.02 else "🟢 Stable"
        pressure_status = "🔴 High" if pore_pressure > 60 else "🟠 Elevated" if pore_pressure > 40 else "🟡 Moderate" if pore_pressure > 20 else "🟢 Normal"

        landslide_prob = min(risk_score / 100, 1.0)
        is_anomaly = tilt_magnitude > 0.05 or soil_moisture > 80

        alerts.append({
            "alert_id": alert_id,
            "node_id": node_id,
            "location_name": location_name,
            "region": "Sikkim, India",
            "lat": lat, "lon": lon,
            "elevation_m": elevation,
            "sensor_type": sensor_type,
            "message": severity_reason,
            "severity": severity,
            "timestamp": timestamp,
            "details": {
                "rainfall_24h_mm": round(rainfall, 1), "rainfall_status": rain_status,
                "soil_moisture_pct": round(soil_moisture, 1), "soil_moisture_status": moisture_status,
                "tilt_x_deg": round(tilt_x, 4), "tilt_y_deg": round(tilt_y, 4),
                "tilt_magnitude": round(tilt_magnitude, 4), "tilt_status": tilt_status,
                "pore_pressure_kpa": round(pore_pressure, 1), "pressure_status": pressure_status,
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
    return [
        {"alert_id": 1, "node_id": "NODE_03", "location_name": "Tadong", "lat": 27.36112, "lon": 88.5891, "message": "Critical tilt detected — Landslide risk!", "severity": "critical", "timestamp": now_iso(), "details": {"soil_moisture": 78.9, "rainfall_24h": 38.4, "tilt_x": 0.0891, "tilt_y": 0.0678, "risk_score": 91.7}},
        {"alert_id": 2, "node_id": "NODE_02", "location_name": "Ranipool", "lat": 27.33421, "lon": 88.6123, "message": "High soil moisture detected (72.3%)", "severity": "warning", "timestamp": now_iso(), "details": {"soil_moisture": 72.3, "rainfall_24h": 31.2, "tilt_x": 0.0678, "tilt_y": 0.0456, "risk_score": 85.2}},
        {"alert_id": 3, "node_id": "NODE_01", "location_name": "Gangtok", "lat": 27.35251, "lon": 88.5746, "message": "Moderate rainfall alert (12.5mm in 24h)", "severity": "info", "timestamp": now_iso(), "details": {"soil_moisture": 45.2, "rainfall_24h": 12.5, "tilt_x": 0.0012, "tilt_y": -0.0023, "risk_score": 45.5}},
    ]


# ================================================================
# ML PREDICTION ENDPOINTS
# ================================================================
@app.get("/api/ml/summary")
def ml_summary():
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

    if 'early_warning' in ml_models:
        try:
            features = [[row['rainfall_24h'], row['rainfall_24h'], row['soil_moisture'], 0, row['soil_moisture'], row['pore_water_pressure'], 0, row['tilt_x'], row['tilt_y'], 0, 0]]
            prob = float(ml_models['early_warning'].predict_proba(features)[0][1])
            result['models']['early_warning'] = {"landslide_probability_24h": round(prob, 4), "prediction": "HIGH RISK" if prob > 0.5 else "LOW RISK"}
        except Exception as e:
            result['models']['early_warning'] = {"error": str(e)}

    if 'anomaly' in ml_models:
        try:
            features = [[row['soil_moisture'], row['pore_water_pressure'], row['tilt_x'], row['tilt_y'], row['rainfall_24h']]]
            pred = ml_models['anomaly'].predict(features)[0]
            score = float(ml_models['anomaly'].score_samples(features)[0])
            result['models']['anomaly'] = {"is_anomaly": bool(pred == -1), "anomaly_score": round(score, 4), "status": "⚠️ ANOMALY DETECTED" if pred == -1 else "✅ Normal"}
        except Exception as e:
            result['models']['anomaly'] = {"error": str(e)}

    if 'susceptibility' in ml_models:
        try:
            features = [[30.0, 1800.0, 2500.0, 2, 1, 150.0, 300.0, 0.3, 3]]
            risk_class = ml_models['susceptibility'].predict(features)[0]
            risk_probs = ml_models['susceptibility'].predict_proba(features)[0]
            classes = ml_models['susceptibility'].classes_
            result['models']['susceptibility'] = {"predicted_risk_level": str(risk_class), "class_probabilities": {str(c): round(float(p), 4) for c, p in zip(classes, risk_probs)}}
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
    roads = [
        {"road_id": "NH10", "name": "NH10 (Gangtok - Singtam)", "status": "open", "condition": "Clear", "length_km": 28.5, "alternate_available": True, "last_checked": now_iso()},
        {"road_id": "NH310", "name": "NH310 (Gangtok - Nathu La)", "status": "slow", "condition": "Waterlogging near 12km mark", "length_km": 52.0, "alternate_available": True, "last_checked": now_iso()},
        {"road_id": "SH1", "name": "SH1 (Tadong - Ranipool)", "status": "blocked", "condition": "Minor landslide debris", "length_km": 8.2, "alternate_available": True, "last_checked": now_iso()},
        {"road_id": "SH2", "name": "SH2 (Gangtok - Pakyong)", "status": "caution", "condition": "Slippery road surface", "length_km": 24.6, "alternate_available": False, "last_checked": now_iso()},
        {"road_id": "SH7", "name": "SH7 (Ranipool - Rongli)", "status": "open", "condition": "Clear", "length_km": 45.3, "alternate_available": True, "last_checked": now_iso()},
    ]
    summary = {
        "total_roads": len(roads),
        "open": sum(1 for r in roads if r["status"] == "open"),
        "slow": sum(1 for r in roads if r["status"] == "slow"),
        "caution": sum(1 for r in roads if r["status"] == "caution"),
        "blocked": sum(1 for r in roads if r["status"] == "blocked"),
        "evacuation_routes_ready": 3,
        "alternate_routes": sum(1 for r in roads if r["alternate_available"]),
    }
    return {"roads": roads, "summary": summary, "last_updated": now_iso()}


# ================================================================
# 🌤️ WEATHER FORECAST
# ================================================================
@app.get("/api/weather-forecast")
def get_weather_forecast():
    today = datetime.now()
    forecast = []
    rainfall_pattern = [45.5, 28.2, 12.8, 8.4]
    risk_pattern = ["critical", "high", "moderate", "low"]
    for i in range(4):
        date = today + timedelta(days=i)
        rainfall = rainfall_pattern[i]
        risk = risk_pattern[i]
       