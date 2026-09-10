import { useEffect, useState } from 'react';

const ToastNotification = ({ alert, onClose, duration = 5000 }) => {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(onClose, 400);
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(onClose, 400);
  };

  const severityColors = {
    critical: '#e94560',
    high: '#ff9f43',
    moderate: '#ffd93d',
    low: '#6bcb77',
  };

  const severityIcons = {
    critical: '🚨',
    high: '⚠️',
    moderate: '👀',
    low: '✅',
  };

  const severity = (alert.severity || 'moderate').toLowerCase();
  const color = severityColors[severity] || '#ffd93d';
  const icon = severityIcons[severity] || '⚠️';
  const d = alert.details || {};

  return (
    <div
      className={`toast-notification ${isExiting ? 'exit' : ''}`}
      style={{ borderLeftColor: color }}
    >
      <div className="toast-header">
        <span className="toast-app-icon" style={{ background: color }}>
          {icon}
        </span>
        <span className="toast-app-name">LANDSLIDE ALERT</span>
        <span className="toast-time">just now</span>
        <button className="toast-close" onClick={handleClose}>✕</button>
      </div>

      <div className="toast-body">
        <div className="toast-title">
          {icon} {severity.toUpperCase()} — {alert.location_name || 'Unknown Location'}
        </div>
        <div className="toast-message">{alert.message}</div>

        {(d.soil_moisture_pct || d.rainfall_24h_mm) && (
          <div className="toast-metrics">
            {d.soil_moisture_pct !== undefined && (
              <span className="toast-metric">💧 {d.soil_moisture_pct}%</span>
            )}
            {d.rainfall_24h_mm !== undefined && (
              <span className="toast-metric">🌧️ {d.rainfall_24h_mm}mm</span>
            )}
            {d.tilt_x_deg !== undefined && (
              <span className="toast-metric">📐 {d.tilt_x_deg}°</span>
            )}
            {d.risk_score !== undefined && (
              <span className="toast-metric">📊 {d.risk_score}/100</span>
            )}
          </div>
        )}

        {alert.recommended_action && (
          <div className="toast-action" style={{ color }}>
            {alert.recommended_action}
          </div>
        )}
      </div>

      <div className="toast-progress">
        <div
          className="toast-progress-fill"
          style={{
            background: color,
            animationDuration: `${duration}ms`,
          }}
        />
      </div>
    </div>
  );
};

export default ToastNotification;