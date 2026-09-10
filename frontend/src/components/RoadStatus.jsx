import { useEffect, useState } from 'react';
import { useLanguage } from '../LanguageContext';

const RoadStatus = () => {
  const { t } = useLanguage();
  const [roads, setRoads] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRoads();
    const interval = setInterval(fetchRoads, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchRoads = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/roads');
      const data = await res.json();
      setRoads(data.roads || []);
      setSummary(data.summary || null);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch roads:', err);
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'open': return '🟢';
      case 'slow': return '🟡';
      case 'caution': return '🟠';
      case 'blocked': return '🔴';
      default: return '⚪';
    }
  };

  const getStatusLabel = (status) => {
    return t(status) || status.toUpperCase();
  };

  if (loading) {
    return (
      <div className="road-status-panel">
        <h3>🛣️ {t('road_status')}</h3>
        <div className="loading-text">Loading...</div>
      </div>
    );
  }

  return (
    <div className="road-status-panel">
      <h3>🛣️ {t('road_status')}</h3>

      {summary && (
        <div className="road-summary">
          <div className="road-summary-item">
            <span className="road-summary-icon">🟢</span>
            <span className="road-summary-value">{summary.open}</span>
            <span className="road-summary-label">{t('open')}</span>
          </div>
          <div className="road-summary-item">
            <span className="road-summary-icon">🟡</span>
            <span className="road-summary-value">{summary.slow}</span>
            <span className="road-summary-label">{t('slow')}</span>
          </div>
          <div className="road-summary-item">
            <span className="road-summary-icon">🟠</span>
            <span className="road-summary-value">{summary.caution}</span>
            <span className="road-summary-label">{t('caution')}</span>
          </div>
          <div className="road-summary-item">
            <span className="road-summary-icon">🔴</span>
            <span className="road-summary-value">{summary.blocked}</span>
            <span className="road-summary-label">{t('blocked')}</span>
          </div>
        </div>
      )}

      <div className="road-list">
        {roads.map((road) => (
          <div key={road.road_id} className={`road-item road-${road.status}`}>
            <div className="road-header">
              <span className="road-icon">{getStatusIcon(road.status)}</span>
              <span className="road-id">{road.road_id}</span>
              <span className={`road-status-badge status-${road.status}`}>
                {getStatusLabel(road.status)}
              </span>
            </div>
            <div className="road-name">{road.name}</div>
            <div className="road-condition">{road.condition}</div>
            <div className="road-meta">
              <span>📏 {road.length_km} km</span>
              {road.alternate_available ? (
                <span className="alt-yes">✅ {t('alt_route')}</span>
              ) : (
                <span className="alt-no">⚠️ {t('no_alt')}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {summary && (
        <div className="evac-info">
          <div className="evac-row">
            <span>🚑 {t('evacuation_routes')}:</span>
            <strong>{summary.evacuation_routes_ready}</strong>
          </div>
          <div className="evac-row">
            <span>🔄 {t('alternate_routes')}:</span>
            <strong>{summary.alternate_routes}</strong>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoadStatus;