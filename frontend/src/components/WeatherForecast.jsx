import { useEffect, useState } from 'react';
import { useLanguage } from '../LanguageContext';

const WeatherForecast = () => {
  const { t } = useLanguage();
  const [forecast, setForecast] = useState([]);
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchForecast();
    const interval = setInterval(fetchForecast, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchForecast = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/weather-forecast');
      const data = await res.json();
      setForecast(data.forecast || []);
      setLocation(data.location || 'Sikkim, India');
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch forecast:', err);
      setLoading(false);
    }
  };

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'critical': return '#e94560';
      case 'high': return '#ff9f43';
      case 'moderate': return '#ffd93d';
      case 'low': return '#6bcb77';
      default: return '#888';
    }
  };

  const getRiskIcon = (risk) => {
    switch (risk) {
      case 'critical': return '🔴';
      case 'high': return '🟠';
      case 'moderate': return '🟡';
      case 'low': return '🟢';
      default: return '⚪';
    }
  };

  const getRainIcon = (rainfall) => {
    if (rainfall > 30) return '⛈️';
    if (rainfall > 15) return '🌧️';
    if (rainfall > 5) return '🌦️';
    return '☁️';
  };

  const getDayLabel = (label) => {
    if (label === 'Today') return t('today');
    if (label === 'Tomorrow') return t('tomorrow');
    return label;
  };

  if (loading) {
    return (
      <div className="weather-panel">
        <h3>🌤️ {t('weather_forecast')}</h3>
        <div className="loading-text">Loading...</div>
      </div>
    );
  }

  return (
    <div className="weather-panel">
      <h3>🌤️ {t('weather_forecast')}</h3>
      <div className="weather-location">📍 {location}</div>

      <div className="forecast-list">
        {forecast.map((day, index) => {
          const riskColor = getRiskColor(day.risk_level);
          return (
            <div
              key={index}
              className={`forecast-item ${day.risk_level}`}
              style={{ borderLeftColor: riskColor }}
            >
              <div className="forecast-header">
                <span className="forecast-day">{getDayLabel(day.day_label)}</span>
                <span className="forecast-date">{day.date}</span>
              </div>

              <div className="forecast-main">
                <span className="forecast-rain-icon">
                  {getRainIcon(day.rainfall_mm)}
                </span>
                <span className="forecast-rainfall">
                  {day.rainfall_mm} mm
                </span>
                <span className="forecast-risk-badge" style={{
                  background: `${riskColor}22`,
                  color: riskColor,
                }}>
                  {getRiskIcon(day.risk_level)} {t(day.risk_level)}
                </span>
              </div>

              <div className="forecast-meta">
                <span>🌡️ {day.temperature_c}°C</span>
                <span>💧 {day.humidity_pct}%</span>
                <span>💨 {day.wind_kph} kph</span>
              </div>

              {day.projected_sensor_risk && (
                <div className="forecast-sensors">
                  <div className="forecast-sensors-title">📡 {t('projected_risk')}</div>
                  <div className="forecast-sensor-grid">
                    {Object.entries(day.projected_sensor_risk)
                      .slice(0, 3)
                      .map(([node, val]) => (
                        <div key={node} className="forecast-sensor-item">
                          <span className="sensor-node">{node}</span>
                          <span className="sensor-val" style={{
                            color: val > 75 ? '#e94560' :
                                   val > 55 ? '#ff9f43' :
                                   val > 35 ? '#ffd93d' : '#6bcb77'
                          }}>
                            {val}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default WeatherForecast;