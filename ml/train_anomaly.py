"""
train_anomaly.py
Isolation Forest for detecting anomalies in sensor data.
Flags equipment failures AND unusual ground behavior.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os

print("=" * 60)
print("🔍 TRAINING ANOMALY DETECTION MODEL (Isolation Forest)")
print("=" * 60)

# ----------------------------------------------------------------
# 1. Load data
# ----------------------------------------------------------------
print("\n📂 Loading sensor data...")
df = pd.read_csv('data/synthetic_sensors.csv')
print(f"   Loaded {len(df)} records")

# ----------------------------------------------------------------
# 2. Train model
# ----------------------------------------------------------------
features = ['soil_moisture', 'pore_pressure', 'tilt_x', 'tilt_y', 'rainfall_24h']
X = df[features].fillna(0)

print(f"\n🎓 Training on {len(X)} samples with {len(features)} features...")

model = IsolationForest(
    contamination=0.05,  # expect 5% anomalies
    random_state=42,
    n_estimators=100,
    n_jobs=-1
)

model.fit(X)

# ----------------------------------------------------------------
# 3. Evaluate
# ----------------------------------------------------------------
predictions = model.predict(X)
df['anomaly'] = predictions
df['anomaly_score'] = model.score_samples(X)

n_anomalies = (df['anomaly'] == -1).sum()

print(f"\n📊 Detected {n_anomalies} anomalies ({n_anomalies/len(df)*100:.1f}%)")
print(f"\n🚨 Sample anomalies:")
anomalies = df[df['anomaly'] == -1].head(5)
print(anomalies[['node_id', 'soil_moisture', 'pore_pressure', 'tilt_x', 'rainfall_24h']].to_string(index=False))

# ----------------------------------------------------------------
# 4. Save
# ----------------------------------------------------------------
os.makedirs('ml/models', exist_ok=True)
joblib.dump(model, 'ml/models/anomaly_model.pkl')
joblib.dump(features, 'ml/models/anomaly_features.pkl')

print(f"\n💾 Model saved to: ml/models/anomaly_model.pkl")
print(f"✅ DONE!\n")
