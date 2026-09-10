import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';

// Fix Leaflet icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const RiskHeatmap = ({ zones = [], sensors = [] }) => {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const heatLayerRef = useRef(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [27.33, 88.61],
      zoom: 10,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    mapRef.current = map;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;

    // Clear old heat layer
    if (heatLayerRef.current) {
      mapRef.current.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
    }

    // Get sensor data for heatmap
    const heatData = sensors.map(sensor => {
      const lat = sensor.lat || sensor.Latitude || 0;
      const lng = sensor.lng || sensor.Longitude || 0;
      const value = sensor.value || sensor.risk_score || 50;
      // Intensity: 0-1 based on risk value
      const intensity = Math.min(value / 100, 1);
      return [lat, lng, intensity];
    });

    // Also add zone centroids as heat points
    let features = [];
    if (zones.type === 'FeatureCollection' && Array.isArray(zones.features)) {
      features = zones.features;
    } else if (Array.isArray(zones)) {
      features = zones;
    }

    features.forEach(feature => {
      try {
        let coords = [];
        if (feature.geometry?.type === 'Polygon') {
          coords = feature.geometry.coordinates[0];
        } else if (feature.coordinates) {
          coords = feature.coordinates;
        }
        
        if (coords && coords.length > 0) {
          // Calculate centroid
          const lat = coords.reduce((sum, c) => sum + c[1], 0) / coords.length;
          const lng = coords.reduce((sum, c) => sum + c[0], 0) / coords.length;
          
          const props = feature.properties || {};
          const score = props.risk_score || 0.5;
          const intensity = Math.min(score * 1.5, 1);
          
          heatData.push([lat, lng, intensity]);
        }
      } catch (e) {}
    });

    if (heatData.length === 0) {
      return;
    }

    // Create heatmap layer
    const heatLayer = L.heatLayer(heatData, {
      radius: 25,
      blur: 15,
      maxZoom: 17,
      gradient: {
        0.0: '#6bcb77',   // Low - Green
        0.25: '#ffd93d',  // Moderate - Yellow
        0.5: '#ff9f43',   // High - Orange
        0.75: '#e94560',  // Critical - Red
        1.0: '#8b0000'    // Extreme - Dark Red
      },
      minOpacity: 0.3,
    });

    heatLayer.addTo(mapRef.current);
    heatLayerRef.current = heatLayer;

    // Fit map to show all data
    if (heatData.length > 0) {
      const bounds = heatData.map(d => [d[0], d[1]]);
      mapRef.current.fitBounds(bounds, { padding: [50, 50] });
    }

  }, [zones, sensors]);

  return (
    <div 
      ref={mapContainerRef} 
      style={{ 
        width: '100%', 
        height: '100%', 
        minHeight: '550px',
        borderRadius: '12px',
        overflow: 'hidden',
      }} 
    />
  );
};

export default RiskHeatmap;