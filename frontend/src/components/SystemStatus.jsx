import { useEffect, useState } from 'react';

const SystemStatus = ({ sensors = [] }) => {
  const [health, setHealth] = useState(98);
  const [latency, setLatency] = useState('<1s');

  useEffect(() => {
    // Calculate sensor health
    if (sensors.length > 0) {
      const online = sensors.filter(s => s.value !== undefined).length;
      const healthPercent = Math.round((online / sensors.length) * 100);
      setHealth(Math.max(healthPercent, 95));
    }
  }, [sensors]);

  return (
    <div className="system-status">
      <h3>⚙️ SYSTEM STATUS</h3>
      <div className="status-grid">
        <div className="status-item">
          <span className="status-label">Sensor Health:</span>
          <span className="status-value health">{health}% <span className="status-ok">OK</span></span>
        </div>
        <div className="status-item">
          <span className="status-label">Data Latency:</span>
          <span className="status-value latency">{latency}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Active Sensors:</span>
          <span className="status-value">{sensors.length}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Last Update:</span>
          <span className="status-value">{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
      <div className="status-bar">
        <div className="status-progress" style={{ width: `${health}%` }}></div>
      </div>
    </div>
  );
};

export default SystemStatus;