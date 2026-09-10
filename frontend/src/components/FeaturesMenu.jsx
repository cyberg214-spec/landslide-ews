import { useState, useRef, useEffect } from 'react';

const FeaturesMenu = ({ activeView, setActiveView }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const features = [
    { id: 'priority', label: 'Priority Zones', icon: '🚨' },
    { id: 'alerts', label: 'Live Alerts', icon: '🔔' },
    { id: 'roads', label: 'Road Status', icon: '🛣️' },
    { id: 'weather', label: 'Weather Forecast', icon: '🌤️' },
    { id: 'legend', label: 'Risk Level', icon: '📊' },
    { id: 'system', label: 'System Status', icon: '⚙️' },
  ];

  const current = features.find((f) => f.id === activeView) || features[0];

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (id) => {
    setActiveView(id);
    setOpen(false);
  };

  return (
    <div className="features-dropdown" ref={ref}>
      <button
        className={`features-trigger ${open ? 'open' : ''}`}
        onClick={() => setOpen(!open)}
      >
        <span className="features-icon">📋</span>
        <span className="features-label">Features</span>
        <span className={`features-arrow ${open ? 'rotated' : ''}`}>▾</span>
      </button>

      {open && (
        <div className="features-menu">
          <div className="features-menu-title">SELECT VIEW</div>
          {features.map((f) => (
            <button
              key={f.id}
              className={`features-option ${activeView === f.id ? 'active' : ''}`}
              onClick={() => handleSelect(f.id)}
            >
              <span className="features-option-icon">{f.icon}</span>
              <span className="features-option-label">{f.label}</span>
              {activeView === f.id && <span className="features-check">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default FeaturesMenu;