const Legend = () => {
  const items = [
    { label: 'Critical', color: '#e94560' },
    { label: 'High', color: '#ff9f43' },
    { label: 'Moderate', color: '#ffd93d' },
    { label: 'Low', color: '#6bcb77' },
  ];

  return (
    <div className="legend-container">
      <h3>📊 RISK LEVEL</h3>
      <div className="legend-grid">
        {items.map((item) => (
          <div key={item.label} className="legend-item">
            <div className="legend-color" style={{ background: item.color }}></div>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Legend;