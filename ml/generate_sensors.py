def create_risk_zones_geojson():
    """Create risk zones in GeoJSON format expected by backend"""
    import os
    import json
    
    zones = [
        {
            "zone_id": "zone_1",
            "name": "North District",
            "risk_level": "high",
            "risk_score": 75,
            "risk_label": "High",
            "color": "#ff6b6b",
            "last_updated": "2026-09-10T10:00:00",
            "coordinates": [
                [88.62, 27.35],
                [88.67, 27.35],
                [88.67, 27.30],
                [88.62, 27.30],
                [88.62, 27.35]
            ]
        },
        {
            "zone_id": "zone_2",
            "name": "East District",
            "risk_level": "moderate",
            "risk_score": 50,
            "risk_label": "Moderate",
            "color": "#ffd93d",
            "last_updated": "2026-09-10T10:00:00",
            "coordinates": [
                [88.60, 27.33],
                [88.65, 27.33],
                [88.65, 27.28],
                [88.60, 27.28],
                [88.60, 27.33]
            ]
        },
        {
            "zone_id": "zone_3",
            "name": "South District",
            "risk_level": "critical",
            "risk_score": 92,
            "risk_label": "Critical",
            "color": "#e94560",
            "last_updated": "2026-09-10T10:00:00",
            "coordinates": [
                [88.56, 27.31],
                [88.61, 27.31],
                [88.61, 27.26],
                [88.56, 27.26],
                [88.56, 27.31]
            ]
        },
        {
            "zone_id": "zone_4",
            "name": "West District",
            "risk_level": "low",
            "risk_score": 25,
            "risk_label": "Low",
            "color": "#6bcb77",
            "last_updated": "2026-09-10T10:00:00",
            "coordinates": [
                [88.52, 27.37],
                [88.57, 27.37],
                [88.57, 27.32],
                [88.52, 27.32],
                [88.52, 27.37]
            ]
        }
    ]
    
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    for zone in zones:
        feature = {
            "type": "Feature",
            "properties": {
                "zone_id": zone["zone_id"],
                "name": zone["name"],
                "risk_level": zone["risk_level"],
                "risk_score": zone["risk_score"],
                "risk_label": zone["risk_label"],
                "color": zone["color"],
                "last_updated": zone["last_updated"]
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [zone["coordinates"]]
            }
        }
        geojson["features"].append(feature)
    
    os.makedirs('data', exist_ok=True)
    with open('data/risk_zones.json', 'w') as f:
        json.dump(geojson, f, indent=2)
    print("✅ Created data/risk_zones.json (GeoJSON format with all required fields)")