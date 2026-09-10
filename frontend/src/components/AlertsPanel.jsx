import { useLanguage } from '../LanguageContext';

const AlertsPanel = ({ alerts = [] }) => {
  const { t } = useLanguage();

  if (!alerts || alerts.length === 0) {
    return (
      <div className="alerts-panel">
        <h3>🔔 {t('live_alerts')} <span className="alert-count">0</span></h3>
        <div className="no-alerts">✅ {t('no_alerts')}</div>
      </div>
    );
  }

  const getSeverityClass = (severity) => {
    const s = (severity || '').toLowerCase();
    if (s.includes('critical')) return 'critical';
    if (s.includes('high') || s.includes('warning')) return 'high';
    if (s.includes('moderate') || s.includes('info')) return 'moderate';
    return 'low';
  };

  const getSeverityIcon = (severity) => {
    const s = (severity || '').toLowerCase();
    if (s.includes('critical')) return '🔴';
    if (s.includes('high') || s.includes('warning')) return '🟠';
    if (s.includes('moderate')) return '🟡';
    return '🟢';
  };

  const getSeverityLabel = (severity) => {
    const s = (severity || '').toLowerCase();
    if (s.includes('critical')) return t('critical').toUpperCase();
    if (s.includes('high') || s.includes('warning')) return t('high').toUpperCase();
    if (s.includes('moderate')) return t('moderate').toUpperCase();
    return t('low').toUpperCase();
  };

  const formatCoords = (lat, lon) => {
    if (lat == null || lon == null) return '—';
    const latDir = lat >= 0 ? 'N' : 'S';
    const lonDir = lon >= 0 ? 'E' : 'W';
    return `${Math.abs(lat).toFixed(4)}°${latDir}, ${Math.abs(lon).toFixed(4)}°${lonDir}`;
  };

  const formatTime = (ts) => {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  };

  return (
    <div className="alerts-panel">
      <h3>🔔 {t('live_alerts')} <span className="alert-count">{alerts.length}</span></h3>

      {alerts.map((alert, index) => {
        const sevClass = getSeverityClass(alert.severity);
        const sevIcon = getSeverityIcon(alert.severity);
        const sevLabel = getSeverityLabel(alert.severity);
        const d = alert.details || {};
        const ai = alert.ai_prediction || {};

        return (
          <div key={alert.alert_id || index} className={`alert-item rich ${sevClass}`}>

            {/* HEADER */}
            <div className="alert-header">
              <span className="alert-icon">{sevIcon}</span>
              <span className={`alert-severity-badge ${sevClass}`}>{sevLabel}</span>
              <span className="alert-node">{alert.node_id}</span>
            </div>

            {/* LOCATION */}
            <div className="alert-location-block">
              <div className="alert-location-name">
                📍 {alert.location_name}{alert.region ? `, ${alert.region}` : ''}
              </div>
              <div className="alert-coords">
                🌐 {formatCoords(alert.lat, alert.lon)}
                {alert.elevation_m ? ` • ⛰️ ${alert.elevation_m}m` : ''}
              </div>
              {alert.sensor_type && (
                <div className="alert-sensor-type">
                  📡 {t('sensor_type')}: {alert.sensor_type}
                </div>
              )}
            </div>

            {/* MESSAGE */}
            <div className="alert-message">{alert.message}</div>

            {/* DETAILS GRID */}
            <div className="alert-metrics">
              <div className="metric-row">
                <span className="metric-label">🌧️ {t('rainfall_24h')}</span>
                <span className="metric-value">
                  {d.rainfall_24h_mm ?? '—'} mm
                  {d.rainfall_status && <span className="metric-status">{d.rainfall_status}</span>}
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-label">💧 {t('soil_moisture')}</span>
                <span className="metric-value">
                  {d.soil_moisture_pct ?? '—'}%
                  {d.soil_moisture_status && <span className="metric-status">{d.soil_moisture_status}</span>}
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-label">📐 {t('tilt')} (X / Y)</span>
                <span className="metric-value">
                  {d.tilt_x_deg ?? '—'}° / {d.tilt_y_deg ?? '—'}°
                  {d.tilt_status && <span className="metric-status">{d.tilt_status}</span>}
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-label">🔬 {t('pore_pressure')}</span>
                <span className="metric-value">
                  {d.pore_pressure_kpa ?? '—'} kPa
                  {d.pressure_status && <span className="metric-status">{d.pressure_status}</span>}
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-label">📊 {t('risk_score')}</span>
                <span className="metric-value">
                  {d.risk_score ?? '—'} / 100
                </span>
              </div>
            </div>

            {/* AI PREDICTION */}
            {(ai.landslide_probability !== undefined || ai.anomaly_detected !== undefined) && (
              <div className="alert-ai-block">
                <div className="ai-title">🤖 {t('ai_prediction')}</div>
                {ai.landslide_probability !== undefined && (
                  <div className="ai-row">
                    <span>{t('landslide_probability')}:</span>
                    <span className="ai-value">
                      {(ai.landslide_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
                {ai.anomaly_detected !== undefined && (
                  <div className="ai-row">
                    <span>{t('anomaly')}:</span>
                    <span className={`ai-value ${ai.anomaly_detected ? 'danger' : 'safe'}`}>
                      {ai.anomaly_detected ? `⚠️ ${t('detected')}` : `✅ ${t('normal')}`}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* ACTION */}
            {alert.recommended_action && (
              <div className={`alert-action ${sevClass}`}>
                {alert.recommended_action}
              </div>
            )}

            {/* TIMESTAMP */}
            <div className="alert-time">🕐 {formatTime(alert.timestamp)}</div>
          </div>
        );
      })}
    </div>
  );
};

export default AlertsPanel;