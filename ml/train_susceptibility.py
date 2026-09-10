"""
train_susceptibility.py
Random Forest model for landslide susceptibility prediction.
Predicts which zones are prone to landslides based on terrain features.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

print("=" * 60)
print("🌲 TRAINING SUSCEPTIBILITY MODEL (Random Forest)")
print("=" * 60)

# ----------------------------------------------------------------
# 1. Generate training data
#    In production: use GSI historical landslide records
# ----------------------------------------------------------------
np.random.seed(42)
n_samples = 5000

data = pd.DataFrame({
    'slope_angle': np.random.uniform(5, 45, n_samples),
    'elevation': np.random.uniform(500, 3500, n_samples),
    'rainfall_avg': np.random.uniform(500, 3000, n_samples),
    'soil_type': np.random.randint(0, 5, n_samples),
    'land_use': np.random.randint(0, 4, n_samples),
    'distance_to_road': np.random.uniform(0, 500, n_samples),
    'distance_to_river': np.random.uniform(0, 1000, n_samples),
    'ndvi': np.random.uniform(-0.2, 0.8, n_samples),
    'lithology': np.random.randint(0, 6, n_samples),
})

# Create realistic risk labels
risk_score = (
    (data['slope_angle'] > 25).astype(int) * 2 +
    (data['rainfall_avg'] > 2000).astype(int) * 2 +
    (data['distance_to_river'] < 200).astype(int) * 1 +
    (data['ndvi'] < 0.2).astype(int) * 1 +
    (data['distance_to_road'] < 100).astype(int) * 1 +
    (data['elevation'] > 2000).astype(int) * 1
)

data['landslide_risk'] = pd.cut(
    risk_score,
    bins=[-1, 1, 3, 5, 8],
    labels=['low', 'moderate', 'high', 'critical']
)

# ----------------------------------------------------------------
# 2. Train model
# ----------------------------------------------------------------
features = ['slope_angle', 'elevation', 'rainfall_avg', 'soil_type',
            'land_use', 'distance_to_road', 'distance_to_river',
            'ndvi', 'lithology']

X = data[features]
y = data['landslide_risk']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# ----------------------------------------------------------------
# 3. Evaluate
# ----------------------------------------------------------------
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n📊 Model Accuracy: {accuracy:.2%}")
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
# 4. Save model
# ----------------------------------------------------------------
os.makedirs('ml/models', exist_ok=True)
joblib.dump(model, 'ml/models/susceptibility_model.pkl')
joblib.dump(features, 'ml/models/susceptibility_features.pkl')

print(f"\n💾 Model saved to: ml/models/susceptibility_model.pkl")
print(f"✅ DONE!\n")