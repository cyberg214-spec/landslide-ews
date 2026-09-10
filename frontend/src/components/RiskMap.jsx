import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Village data for Sikkim region
const VILLAGES = [
  { name: 'Gangtok', lat: 27.3389, lon: 88.6065, population: '100,286', priority: 'high' },
  { name: 'Tadong', lat: 27.3167, lon: 88.6167, population: '12,500', priority: 'critical' },
  { name: 'Ranipool', lat: 27.2986, lon: 88.5872, population: '8,200', priority: 'high' },
  { name: 'Pakyong', lat: 27.2333, lon: 88.5833, population: '5,400', priority: 'moderate' },
  { name: 'Rongli', lat: 27.2167, lon: 88.6667, population: '3,800', priority: 'moderate' },
  { name: 'Ravangla', lat: 27.3000, lon: 88.3667, population: '2,900', priority: 'low' },
  { name: 'Namchi', lat: 27.1667, lon: 88.3500, population: '12,190', priority: 'moderate' },
  { name: 'Singtam', lat: 27.2333, lon: 88.5000, population: '5,800', priority: 'high' },
  { name: 'Mangan', lat: 27.5167, lon: 88.5333, population: '4,200', priority: 'moderate' },
];

// Safe zones (shelters, hospitals)
const SAFE_ZONES = [
  { name: 'STNM Hospital', lat: 27.3400, lon: 88.6100, type: 'hospital' },
  { name: 'Gangtok Shelter A', lat: 27.3450, lon: 88.6150, type: 'shelter' },
  { name: 'Tadong School', lat: 27.3200, lon: 88.6200, type: 'shelter' },
];

const RiskMap = ({ zones = [], sensors = [], photos = [], impacts = [] }) => {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const layersRef = useRef({
    zones: null,
    sensors: null,
    villages: null,
    safeZones: null,
    photos: null,
    impacts: null,
  });
  const [mapReady, setMapReady] = useState(false);
  const [layers, setLayers] = useState({
    zones: true,
    sensors: true,
    villages: true,
    safeZones: true,
    photos: true,
    impacts: true,
  });

  // Initialize map
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
    setMapReady(true);

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        setMapReady(false);
      }
    };
  }, []);

  // Render zones
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    if (layersRef.current.zones) {
      mapRef.current.removeLayer(layersRef.current.zones);
      layersRef.current.zones = null;
    }

    if (!layers.zones) return;

    let features = [];
    if (zones.type === 'FeatureCollection' && Array.isArray(zones.features)) {
      features = zones.features;
    } else if (Array.isArray(zones)) {
      features = zones;
    }

    if (features.length === 0) return;

    const zoneLayer = L.layerGroup();
    const riskColors = {
      low: '#6bcb77',
      moderate: '#ffd93d',
      high: '#ff9f43',
      critical: '#e94560'
    };

    const zoneNames = {
      'ZONE_01': 'North District',
      'ZONE_02': 'East District',
      'ZONE_03': 'South District',
      'ZONE_04': 'West District',
      'ZONE_05': 'Central District',
    };

    const zonePop = {
      'ZONE_01': '15,000',
      'ZONE_02': '22,000',
      'ZONE_03': '8,000',
      'ZONE_04': '35,000',
    };

    features.forEach((feature, index) => {
      try {
        let coords = [];
        if (feature.geometry?.type === 'Polygon') {
          coords = feature.geometry.coordinates[0];
        } else if (feature.coordinates) {
          coords = feature.coordinates;
        }

        if (!coords || coords.length < 3) return;

        const props = feature.properties || {};
        const riskLabel = (props.risk_label || props.risk_level || 'low').toLowerCase();
        const color = riskColors[riskLabel] || '#ffd93d';
        const zoneId = props.zone_id || `ZONE_0${index + 1}`;
        const zoneName = zoneNames[zoneId] || zoneId;
        const pop = zonePop[zoneId] || '10,000';
        const riskScore = ((props.risk_score || 0.5) * 100).toFixed(0);

        const latSum = coords.reduce((s, c) => s + c[1], 0);
        const lngSum = coords.reduce((s, c) => s + c[0], 0);
        const centroid = [latSum / coords.length, lngSum / coords.length];

        const polygon = L.polygon(coords, {
          color: color,
          weight: 3,
          opacity: 0.8,
          fillColor: color,
          fillOpacity: 0.35,
        });

        polygon.bindPopup(`
          <div style="min-width: 220px; font-family: sans-serif;">
            <h3 style="margin: 0 0 8px 0; color: ${color}; font-size: 15px;">
              ⚠️ ${zoneName}
            </h3>
            <table style="font-size: 12px; width: 100%;">
              <tr><td style="color:#888;">Zone ID:</td><td><strong>${zoneId}</strong></td></tr>
              <tr><td style="color:#888;">Risk Level:</td><td><strong style="color:${color};">${riskLabel.toUpperCase()}</strong></td></tr>
              <tr><td style="color:#888;">Risk Score:</td><td><strong>${riskScore}/100</strong></td></tr>
              <tr><td style="color:#888;">Population:</td><td><strong>${pop}</strong></td></tr>
              <tr><td style="color:#888;">Area:</td><td><strong>~25 km²</strong></td></tr>
              <tr><td style="color:#888;">Last Updated:</td><td><strong>${new Date().toLocaleTimeString()}</strong></td></tr>
            </table>
          </div>
        `);

        polygon.addTo(zoneLayer);

        const label = L.marker(centroid, {
          icon: L.divIcon({
            className: 'zone-label',
            html: `
              <div style="
                background: ${color};
                color: #0a0a1a;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                white-space: nowrap;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                border: 2px solid #fff;
              ">
                ${zoneName}<br>
                <span style="font-size: 10px;">${riskLabel.toUpperCase()}</span>
              </div>
            `,
            iconSize: [100, 30],
            iconAnchor: [50, 15],
          }),
          interactive: false,
        });
        label.addTo(zoneLayer);

      } catch (error) {
        console.error('Error rendering zone:', error);
      }
    });

    zoneLayer.addTo(mapRef.current);
    layersRef.current.zones = zoneLayer;

  }, [zones, mapReady, layers.zones]);

  // Render sensors
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    if (layersRef.current.sensors) {
      mapRef.current.removeLayer(layersRef.current.sensors);
      layersRef.current.sensors = null;
    }

    if (!layers.sensors) return;
    if (!sensors || sensors.length === 0) return;

    const sensorLayer = L.layerGroup();

    sensors.forEach((sensor) => {
      try {
        const lat = sensor.lat || sensor.Latitude;
        const lng = sensor.lng || sensor.lon || sensor.Longitude;

        if (!lat || !lng) return;

        const value = sensor.risk_score || sensor.value || 50;
        let color = '#6bcb77';
        let riskLevel = 'Low';
        if (value > 75) { color = '#e94560'; riskLevel = 'Critical'; }
        else if (value > 55) { color = '#ff9f43'; riskLevel = 'High'; }
        else if (value > 35) { color = '#ffd93d'; riskLevel = 'Moderate'; }

        const isCritical = value > 75;

        const marker = L.circleMarker([lat, lng], {
          radius: isCritical ? 12 : 9,
          color: '#fff',
          weight: 2,
          fillColor: color,
          fillOpacity: 0.9,
        });

        marker.bindPopup(`
          <div style="min-width: 240px; font-family: sans-serif;">
            <h3 style="margin: 0 0 8px 0; color: ${color}; font-size: 14px;">
              📡 ${sensor.node_id || 'Sensor'}
            </h3>
            <div style="background: ${color}22; padding: 6px 8px; border-radius: 4px; margin-bottom: 8px;">
              <strong style="color: ${color};">${riskLevel} Risk</strong>
              <span style="float: right;">${value.toFixed(1)}/100</span>
            </div>
            <table style="font-size: 12px; width: 100%;">
              <tr><td style="color:#888;">🌧️ Rainfall 24h:</td><td><strong>${(sensor.rainfall_24h || 0).toFixed(1)} mm</strong></td></tr>
              <tr><td style="color:#888;">💧 Soil Moisture:</td><td><strong>${(sensor.soil_moisture || 0).toFixed(1)}%</strong></td></tr>
              <tr><td style="color:#888;">📐 Tilt X / Y:</td><td><strong>${(sensor.tilt_x || 0).toFixed(4)}° / ${(sensor.tilt_y || 0).toFixed(4)}°</strong></td></tr>
              <tr><td style="color:#888;">🔬 Pore Pressure:</td><td><strong>${(sensor.pore_water_pressure || 0).toFixed(1)} kPa</strong></td></tr>
              <tr><td style="color:#888;">📍 Coordinates:</td><td><strong>${lat.toFixed(4)}, ${lng.toFixed(4)}</strong></td></tr>
              <tr><td style="color:#888;">🕐 Updated:</td><td><strong>${sensor.timestamp || 'Just now'}</strong></td></tr>
            </table>
          </div>
        `);

        marker.addTo(sensorLayer);

      } catch (error) {
        console.error('Error rendering sensor:', error);
      }
    });

    sensorLayer.addTo(mapRef.current);
    layersRef.current.sensors = sensorLayer;

  }, [sensors, mapReady, layers.sensors]);

  // Render villages
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    if (layersRef.current.villages) {
      mapRef.current.removeLayer(layersRef.current.villages);
      layersRef.current.villages = null;
    }

    if (!layers.villages) return;

    const villageLayer = L.layerGroup();

    const priorityColors = {
      critical: '#e94560',
      high: '#ff9f43',
      moderate: '#ffd93d',
      low: '#6bcb77',
    };

    VILLAGES.forEach(village => {
      const color = priorityColors[village.priority] || '#888';

      const marker = L.marker([village.lat, village.lon], {
        icon: L.divIcon({
          className: 'village-marker',
          html: `
            <div style="
              background: ${color};
              color: #fff;
              padding: 3px 8px;
              border-radius: 12px;
              font-size: 10px;
              font-weight: 700;
              white-space: nowrap;
              box-shadow: 0 2px 4px rgba(0,0,0,0.5);
              border: 1.5px solid #fff;
            ">
              🏘️ ${village.name}
            </div>
          `,
          iconSize: [80, 20],
          iconAnchor: [40, 10],
        }),
      });

      marker.bindPopup(`
        <div style="min-width: 180px; font-family: sans-serif;">
          <h3 style="margin: 0 0 8px 0; color: ${color};">🏘️ ${village.name}</h3>
          <table style="font-size: 12px; width: 100%;">
            <tr><td style="color:#888;">Population:</td><td><strong>${village.population}</strong></td></tr>
            <tr><td style="color:#888;">Priority:</td><td><strong style="color:${color};">${village.priority.toUpperCase()}</strong></td></tr>
            <tr><td style="color:#888;">Coordinates:</td><td><strong>${village.lat}, ${village.lon}</strong></td></tr>
          </table>
        </div>
      `);

      marker.addTo(villageLayer);
    });

    villageLayer.addTo(mapRef.current);
    layersRef.current.villages = villageLayer;

  }, [mapReady, layers.villages]);

  // Render safe zones
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    if (layersRef.current.safeZones) {
      mapRef.current.removeLayer(layersRef.current.safeZones);
      layersRef.current.safeZones = null;
    }

    if (!layers.safeZones) return;

    const safeLayer = L.layerGroup();

    SAFE_ZONES.forEach(zone => {
      const icon = zone.type === 'hospital' ? '🏥' : '🏫';

      const marker = L.marker([zone.lat, zone.lon], {
        icon: L.divIcon({
          className: 'safe-zone-marker',
          html: `
            <div style="
              background: #00d4ff;
              color: #0a0a1a;
              width: 28px;
              height: 28px;
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 14px;
              box-shadow: 0 2px 6px rgba(0,212,255,0.6);
              border: 2px solid #fff;
            ">
              ${icon}
            </div>
          `,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        }),
      });

      marker.bindPopup(`
        <div style="font-family: sans-serif;">
          <h3 style="margin: 0 0 6px 0; color: #00d4ff;">${icon} ${zone.name}</h3>
          <p style="font-size: 12px; color: #888; margin: 0;">
            Type: ${zone.type.toUpperCase()}<br>
            Emergency safe zone
          </p>
        </div>
      `);

      marker.addTo(safeLayer);
    });

    safeLayer.addTo(mapRef.current);
    layersRef.current.safeZones = safeLayer;

  }, [mapReady, layers.safeZones]);

  // Render photo markers (citizen reports)
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    if (layersRef.current.photos) {
      mapRef.current.removeLayer(layersRef.current.photos);
      layersRef.current.photos = null;
    }

    if (!layers.photos) return;
    if (!photos || photos.length === 0) return;

    const photoLayer = L.layerGroup();

    const categoryIcons = {
      crack: { emoji: '🔴', label: 'Crack', color: '#e94560' },
      slope: { emoji: '🟠', label: 'Slope Movement', color: '#ff9f43' },
      blocked: { emoji: '🟡', label: 'Blocked Road', color: '#ffd93d' },
      other: { emoji: '⚪', label: 'Other', color: '#888888' },
    };

    photos.forEach((photo) => {
      try {
        if (!photo.lat || !photo.lon) return;

        const cat = categoryIcons[photo.category] || categoryIcons.other;
        const photoUrl = photo.photo_url || '';

        const marker = L.marker([photo.lat, photo.lon], {
          icon: L.divIcon({
            className: 'photo-marker',
            html: `
              <div style="
                background: ${cat.color};
                width: 34px;
                height: 34px;
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                border: 3px solid #fff;
                box-shadow: 0 3px 10px rgba(0,0,0,0.6);
                display: flex;
                align-items: center;
                justify-content: center;
              ">
                <span style="transform: rotate(45deg); font-size: 15px;">📸</span>
              </div>
            `,
            iconSize: [34, 34],
            iconAnchor: [17, 34],
            popupAnchor: [0, -34],
          }),
        });

        marker.bindPopup(`
          <div style="min-width: 240px; font-family: sans-serif;">
            <div style="
              background: ${cat.color};
              color: #fff;
              padding: 4px 10px;
              border-radius: 4px;
              font-size: 11px;
              font-weight: 700;
              display: inline-block;
              margin-bottom: 8px;
            ">
              ${cat.emoji} ${cat.label.toUpperCase()}
            </div>
            ${photoUrl ? `<img src="${photoUrl}" style="width: 100%; border-radius: 6px; margin-bottom: 8px; max-height: 200px; object-fit: cover;" />` : ''}
            <p style="font-size: 12px; margin: 4px 0; color: #333;">
              <strong>Description:</strong><br>
              ${photo.description || 'No description'}
            </p>
            <p style="font-size: 11px; margin: 4px 0; color: #888;">
              📍 ${photo.lat.toFixed(5)}, ${photo.lon.toFixed(5)}<br>
              👤 ${photo.reporter || 'Anonymous'}<br>
              🕐 ${photo.timestamp || 'Just now'}
            </p>
          </div>
        `);

        marker.addTo(photoLayer);

      } catch (error) {
        console.error('Error rendering photo:', error);
      }
    });

    photoLayer.addTo(mapRef.current);
    layersRef.current.photos = photoLayer;

  }, [photos, mapReady, layers.photos]);

  // Render impact zones
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    if (layersRef.current.impacts) {
      mapRef.current.removeLayer(layersRef.current.impacts);
      layersRef.current.impacts = null;
    }

    if (!layers.impacts) return;
    if (!impacts || impacts.length === 0) return;

    const impactLayer = L.layerGroup();

    const severityColors = {
      critical: '#e94560',
      high: '#ff9f43',
      moderate: '#ffd93d',
      low: '#6bcb77',
    };

    const typeIcons = {
      debris_flow: '🌊',
      slope_failure: '⛰️',
      saturation: '💧',
      flood_risk: '🌊',
      watch: '👀',
    };

    impacts.forEach((impact) => {
      try {
        const color = severityColors[impact.severity] || '#888';
        const icon = typeIcons[impact.type] || '⚠️';

        // Impact circle
        const circle = L.circle(impact.center, {
          radius: impact.radius_m,
          color: color,
          weight: 2,
          opacity: 0.8,
          fillColor: color,
          fillOpacity: 0.15,
          dashArray: impact.severity === 'critical' ? '10, 5' : null,
        });

        circle.bindPopup(`
          <div style="min-width: 280px; font-family: sans-serif;">
            <div style="
              background: ${color};
              color: #fff;
              padding: 6px 10px;
              border-radius: 6px;
              font-size: 11px;
              font-weight: 700;
              display: inline-block;
              margin-bottom: 10px;
              text-transform: uppercase;
              letter-spacing: 1px;
            ">
              ${icon} ${impact.severity} IMPACT ZONE
            </div>
            <h3 style="margin: 0 0 10px 0; color: #333; font-size: 15px;">
              🎯 ${impact.location_name}
            </h3>

            <div style="background: #f5f5f5; padding: 8px; border-radius: 6px; margin-bottom: 10px;">
              <div style="font-size: 11px; color: #666; margin-bottom: 4px;">IMPACT TYPE</div>
              <div style="font-size: 13px; font-weight: 700; color: ${color};">
                ${icon} ${impact.type.replace('_', ' ').toUpperCase()}
              </div>
              <div style="font-size: 11px; color: #666; margin-top: 4px;">
                Radius: ${impact.radius_m}m
              </div>
            </div>

            <table style="font-size: 12px; width: 100%; margin-bottom: 8px;">
              <tr>
                <td style="color:#888; padding: 3px 0;">👥 Population at Risk</td>
                <td style="text-align: right;"><strong>${impact.population.toLocaleString()}</strong></td>
              </tr>
              <tr>
                <td style="color:#888; padding: 3px 0;">⏱️ Evacuation Time</td>
                <td style="text-align: right;"><strong>${impact.evacuation_time_min} min</strong></td>
              </tr>
              <tr>
                <td style="color:#888; padding: 3px 0;">📊 Risk Score</td>
                <td style="text-align: right;"><strong style="color:${color};">${impact.metrics.risk_score}/100</strong></td>
              </tr>
              <tr>
                <td style="color:#888; padding: 3px 0;">💧 Soil Moisture</td>
                <td style="text-align: right;"><strong>${impact.metrics.soil_moisture}%</strong></td>
              </tr>
            </table>

            ${impact.villages && impact.villages.length > 0 ? `
              <div style="margin-bottom: 8px;">
                <div style="font-size: 11px; color: #666; margin-bottom: 3px;">🏘️ VILLAGES AFFECTED</div>
                <div style="font-size: 12px; color: #333;">
                  ${impact.villages.join(', ')}
                </div>
              </div>
            ` : ''}

            ${impact.roads && impact.roads.length > 0 ? `
              <div style="margin-bottom: 8px;">
                <div style="font-size: 11px; color: #666; margin-bottom: 3px;">🛣️ ROADS AFFECTED</div>
                <div style="font-size: 12px; color: #333;">
                  ${impact.roads.join(', ')}
                </div>
              </div>
            ` : ''}

            ${impact.shelters && impact.shelters.length > 0 ? `
              <div style="margin-bottom: 8px;">
                <div style="font-size: 11px; color: #666; margin-bottom: 3px;">🏥 SHELTERS IN ZONE</div>
                <div style="font-size: 12px; color: #333;">
                  ${impact.shelters.join(', ')}
                </div>
              </div>
            ` : ''}

            <div style="
              background: ${color};
              color: #fff;
              padding: 8px 12px;
              border-radius: 6px;
              text-align: center;
              font-size: 13px;
              font-weight: 700;
              margin-top: 10px;
            ">
              ${impact.recommended_action}
            </div>
          </div>
        `);

        circle.addTo(impactLayer);

        // Add center marker with type icon
        const marker = L.marker(impact.center, {
          icon: L.divIcon({
            className: 'impact-marker',
            html: `
              <div style="
                background: ${color};
                color: #fff;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                box-shadow: 0 3px 10px ${color}88;
                border: 3px solid #fff;
              ">
                ${icon}
              </div>
            `,
            iconSize: [36, 36],
            iconAnchor: [18, 18],
          }),
        });

        marker.addTo(impactLayer);

      } catch (error) {
        console.error('Error rendering impact zone:', error);
      }
    });

    impactLayer.addTo(mapRef.current);
    layersRef.current.impacts = impactLayer;

  }, [impacts, mapReady, layers.impacts]);

  const toggleLayer = (layerName) => {
    setLayers(prev => ({ ...prev, [layerName]: !prev[layerName] }));
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {/* Layer Toggle Panel */}
      <div className="layer-toggle-panel">
        <div className="layer-panel-title">🗂️ Layers</div>
        <label className="layer-toggle">
          <input
            type="checkbox"
            checked={layers.zones}
            onChange={() => toggleLayer('zones')}
          />
          <span>⚠️ Risk Zones</span>
        </label>
        <label className="layer-toggle">
          <input
            type="checkbox"
            checked={layers.sensors}
            onChange={() => toggleLayer('sensors')}
          />
          <span>📡 Sensors</span>
        </label>
        <label className="layer-toggle">
          <input
            type="checkbox"
            checked={layers.villages}
            onChange={() => toggleLayer('villages')}
          />
          <span>🏘️ Villages</span>
        </label>
        <label className="layer-toggle">
          <input
            type="checkbox"
            checked={layers.safeZones}
            onChange={() => toggleLayer('safeZones')}
          />
          <span>🏥 Safe Zones</span>
        </label>
        <label className="layer-toggle">
          <input
            type="checkbox"
            checked={layers.photos}
            onChange={() => toggleLayer('photos')}
          />
          <span>📸 Photos</span>
        </label>
        <label className="layer-toggle">
          <input
            type="checkbox"
            checked={layers.impacts}
            onChange={() => toggleLayer('impacts')}
          />
          <span>🎯 Impact Zones</span>
        </label>
      </div>

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
    </div>
  );
};

export default RiskMap;