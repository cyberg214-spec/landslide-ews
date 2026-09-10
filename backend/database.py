"""
database.py
SQLite setup for SIH 26001 backend. SQLite instead of PostGIS by design —
this is a scope cut for a solo build; geometry is stored as plain GeoJSON
text since we don't need spatial SQL queries for a hackathon demo.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

# Fixed rule, same convention as the ml/ scripts: data/ lives one level
# up from this script's folder (sih26001/data/, this script is in backend/).
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(HERE, "app.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS risk_zones (
            zone_id TEXT PRIMARY KEY,
            geometry TEXT NOT NULL,
            risk_score REAL NOT NULL,
            risk_label TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_nodes (
            node_id TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            soil_moisture REAL,
            pore_water_pressure REAL,
            tilt_x REAL,
            tilt_y REAL,
            rainfall_24h REAL,
            risk_score REAL,
            risk_label TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_node ON sensor_readings(node_id, timestamp)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            lat REAL,
            lon REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS field_reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            lat REAL,
            lon REAL,
            timestamp TEXT,
            photo_path TEXT,
            notes TEXT,
            status TEXT DEFAULT 'received'
        )
    """)

    conn.commit()
    conn.close()


def load_static_zones():
    """Loads risk_zones.json (from ml/train_susceptibility.py output) into the DB.
    Safe to call every startup — uses INSERT OR REPLACE."""
    zones_path = os.path.join(DATA_DIR, "risk_zones.json")
    if not os.path.exists(zones_path):
        raise FileNotFoundError(
            f"Couldn't find {zones_path}. Run ml/train_susceptibility.py first."
        )

    with open(zones_path) as f:
        geojson = json.load(f)

    conn = get_conn()
    cur = conn.cursor()
    for feature in geojson["features"]:
        props = feature["properties"]
        cur.execute("""
            INSERT OR REPLACE INTO risk_zones (zone_id, geometry, risk_score, risk_label, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (
            props["zone_id"],
            json.dumps(feature["geometry"]),
            props["risk_score"],
            props["risk_label"],
            props["last_updated"],
        ))
    conn.commit()
    conn.close()
    print(f"Loaded {len(geojson['features'])} static zones from {zones_path}")


def now_iso():
    return datetime.now(timezone.utc).isoformat()
