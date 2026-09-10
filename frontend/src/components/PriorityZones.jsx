import { useEffect, useState } from 'react';
import { useLanguage } from '../LanguageContext';

const PriorityZones = () => {
  const { t } = useLanguage();
  const [zones, setZones] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPriority();
    const interval = setInterval(fetchPriority, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchPriority = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/priority-zones');
      const data = await res.json();
      setZones(data.priority_zones || []);
      setSummary(data.summary || null);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch priority zones:', err);
      setLoading(false);
    }
  };

  const getUrgencyColor = (urgency) => {
    switch (urgency) {
      case 'critical': return '#e94560';
      case 'high': return '#ff9f43';
      case 'moderate': return '#ffd93d';
      case 'low': return '#6bcb77';
      default: return '#888';
    }
  };

  const getUrgencyIcon = (urgency) => {
    switch (urgency) {
      case 'critical': return '🔴';
      case 'high': return '🟠';
      case 'moderate': return '🟡';
      case 'low': return '🟢';
      default: return '⚪';
    }
  };

  const getUrgencyLabel = (urgency) => {
    return t(urgency) || urgency.toUpperCase();
  };

  const getActionLabel = (urgency) => {
    if (urgency === 'critical') return t('evacuate_now');
    if (urgency === 'high') return t('prepare_evac');
    if (urgency === 'moderate') return t('issue_advisory');
    return t('monitor');
  };

  const formatPop = (n) => {
    if (n >= 100000) return `${(n / 1000).toFixed(0)}K`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  if (loading) {
    return (
      <div className="priority-panel">
        <h3>🚨 {t('priority_zones')}</h3>
        <div className="loading-text">Loading...</div>
      </div>
    );
  }

  return (
    <div className="priority-panel">
      <h3>🚨 {t('priority_zones')}</h3>

      {summary && (
        <div className="priority-summary">
          <div className="priority-summary-grid">
            <div className="priority-stat">
              <span className="stat-value critical">{summary.critical_count}</span>
              <span className="stat-label">{t('critical')}</span>
            </div>
            <div className="priority-stat">
              <span className="stat-value high">{summary.high_count}</span>
              <span className="stat-label">{t('high')}</span>
            </div>
            <div className="priority-stat">
              <span className="stat-value">{summary.teams_deployed}</span>
              <span className="stat-label">{t('teams')}</span>
            </div>
            <div className="priority-stat">
              <span className="stat-value">{summary.avg_response_time_min}m</span>
              <span className="stat-label">{t('avg_time')}</span>
            </div>
          </div>

          <div className="priority-at-risk">
            <span className="at-risk-label">👥 {t('population_at_risk')}:</span>
            <span className="at-risk-value">{summary.total_population_at_risk.toLocaleString()}</span>
          </div>
        </div>
      )}

      <div className="priority-list">
        {zones.map((zone) => {
          const color = getUrgencyColor(zone.urgency);
          const icon = getUrgencyIcon(zone.urgency);
          const urgencyLabel = getUrgencyLabel(zone.urgency);
          const actionLabel = getActionLabel(zone.urgency);

          return (
            <div
              key={zone.node_id}
              className={`priority-item ${zone.urgency}`}
              style={{ borderLeftColor: color }}
            >
              <div className="priority-header">
                <span className="priority-rank">#{zone.rank}</span>
                <span className="priority-zone">{zone.zone}</span>
                <span className="priority-badge" style={{
                  background: `${color}22`,
                  color: color,
                }}>
                  {icon} {urgencyLabel}
                </span>
              </div>

              <div className="priority-stats">
                <div className="priority-stat-row">
                  <span className="stat-icon">👥</span>
                  <span className="stat-name">{t('population')}</span>
                  <span className="stat-val">{formatPop(zone.population)}</span>
                </div>
                <div className="priority-stat-row">
                  <span className="stat-icon">⚠️</span>
                  <span className="stat-name">{t('risk_score')}</span>
                  <span className="stat-val" style={{ color }}>
                    {zone.risk_score}/100
                  </span>
                </div>
                <div className="priority-stat-row">
                  <span className="stat-icon">📡</span>
                  <span className="stat-name">{t('node')}</span>
                  <span className="stat-val">{zone.node_id}</span>
                </div>
                <div className="priority-stat-row">
                  <span className="stat-icon">⏱️</span>
                  <span className="stat-name">{t('response')}</span>
                  <span className="stat-val">{zone.response_time_min} min</span>
                </div>
              </div>

              <div className="priority-action" style={{
                background: `${color}15`,
                color: color,
              }}>
                {actionLabel}
              </div>

              <div className="priority-score-bar">
                <div
                  className="priority-score-fill"
                  style={{
                    width: `${Math.min(zone.priority_score, 100)}%`,
                    background: color,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PriorityZones;