import pandas as pd
import os

# Path to your CSV
csv_path = "data/synthetic_sensors.csv"

# Read the CSV
df = pd.read_csv(csv_path)

# Show current columns
print("Current columns:", df.columns.tolist())

# Rename columns to match what simulator.py expects
# Add both versions to be safe
df_renamed = df.copy()

# Ensure we have 'timestamp' (lowercase)
if 'Timestamp' in df_renamed.columns and 'timestamp' not in df_renamed.columns:
    df_renamed['timestamp'] = df_renamed['Timestamp']
elif 'timestamp' not in df_renamed.columns and 'Timestamp' not in df_renamed.columns:
    # Create timestamp column from existing data
    df_renamed['timestamp'] = '2026-09-10 10:00:00'

# Ensure we have 'Node_ID' (with underscore, capital N and ID)
if 'node_id' in df_renamed.columns and 'Node_ID' not in df_renamed.columns:
    df_renamed['Node_ID'] = df_renamed['node_id']
elif 'Node_ID' not in df_renamed.columns and 'node_id' not in df_renamed.columns:
    # Create Node_ID column
    df_renamed['Node_ID'] = [f'NODE_{i:02d}' for i in range(1, len(df_renamed) + 1)]

# Ensure we have 'node_id' (lowercase) as well
if 'Node_ID' in df_renamed.columns and 'node_id' not in df_renamed.columns:
    df_renamed['node_id'] = df_renamed['Node_ID']

# Make sure lat/lng exist
if 'lat' not in df_renamed.columns:
    df_renamed['lat'] = 27.35
if 'lng' not in df_renamed.columns:
    df_renamed['lng'] = 88.58

# Make sure value exists
if 'value' not in df_renamed.columns:
    df_renamed['value'] = 50.0

# Make sure sensor_type exists
if 'sensor_type' not in df_renamed.columns:
    df_renamed['sensor_type'] = 'flood'

# Save with both sets of column names
df_renamed.to_csv(csv_path, index=False)

print("✅ Fixed CSV columns!")
print("New columns:", df_renamed.columns.tolist())
print(f"\nSaved to: {csv_path}")
print("\nNow run: cd backend && uvicorn main:app --reload --port 8000")