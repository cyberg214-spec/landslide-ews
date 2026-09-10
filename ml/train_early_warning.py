"""
train_early_warning.py
Gradient Boosting model for landslide early warning.
Predicts if a landslide will occur in the next 24 hours based on sensor patterns.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
import joblib
import os

print("=" * 60)
print("⚡ TRAINING EARLY WARNING MODEL (Gradient Boosting)")
print("=" * 60)

# ----------------------------------------------------------------
# 1. Load sensor data
# ----------------------------------------------------------------
print("\n📂 Loading sensor data...")
df = pd.read_csv('data/synthetic_sensors.csv')
print(f"   Loaded {len(df)} records")

# Sort by node and time
df = df.sort_values(['node_id', 'timestamp']).reset_index(drop=True)

# ----------------------------------------------------------------
# 2. Feature engineering
# ----------------------------------------------------------------
print("\n🔧 Engineering features...")

# Change rates
df['moisture_change'] = df.groupby('node_id')['soil_moisture'].diff().fillna(0)
df['tilt_rate_x'] = df.groupby('node_id')['tilt_x'].diff().fillna(0)
df['tilt_rate_y'] = df.groupby('node_id')['tilt_y'].diff().fillna(0)
df['pressure_change'] = df.groupby('node_id')['pore_pressure'].diff().fillna(0)

# Rolling windows
df['rainfall_6h'] = df.groupby('node_id')['rainfall_24h'].transform(
    lambda x: x.rolling(6, min_periods=1).mean()
)
df['moisture_avg_6h'] = df.groupby('node_id')['soil_moisture'].transform(
    lambda x: x.rolling(6, min_periods=1).mean()
)

# Target: high risk event
df['event'] = (df['value'] > 70).astype(int)

print(f"   Positive events: {df['event'].sum()} / {len(df)}")

# ----------------------------------------------------------------
# 3. Train model
# ----------------------------------------------------------------
features = [
    'rainfall_24h', 'rainfall_6h', 'soil_moisture', 'moisture_change',
    'moisture_avg_6h', 'pore_pressure', 'pressure_change',
    'tilt_x', 'tilt_y', 'tilt_rate_x', 'tilt_rate_y'
]

X = df[features].fillna(0)
y = df['event']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n🎓 Training on {len(X_train)} samples...")

model = GradientBoostingClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=4,
    random_state=42
)

model.fit(X_train, y_train)

# ----------------------------------------------------------------
# 4. Evaluate
# ----------------------------------------------------------------
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_prob)

print(f"\n📊 Model Accuracy: {accuracy:.2%}")
print(f"📊 ROC-AUC Score: {auc:.4f}")
print(f"\n📋 Classification Report:")
print(classification_report(y_test, y_pred, zero_division=0))

# Feature importance
importance = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(f"\n🎯 Top 5 Most Important Features:")
print(importance.head(5).to_string(index=False))

# ----------------------------------------------------------------
# 5. Save
# ----------------------------------------------------------------
os.makedirs('ml/models', exist_ok=True)
joblib.dump(model, 'ml/models/early_warning_model.pkl')
joblib.dump(features, 'ml/models/early_warning_features.pkl')

print(f"\n💾 Model saved to: ml/models/early_warning_model.pkl")
print(f"✅ DONE!\n")