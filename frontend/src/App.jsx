import { useEffect, useState } from 'react';
import './index.css';
import RiskMap from './components/RiskMap';
import AlertsPanel from './components/AlertsPanel';
import Legend from './components/Legend';
import SystemStatus from './components/SystemStatus';
import RoadStatus from './components/RoadStatus';
import WeatherForecast from './components/WeatherForecast';
import PriorityZones from './components/PriorityZones';
import LanguageToggle from './components/LanguageToggle';
import FeaturesMenu from './components/FeaturesMenu';
import PhotoUpload from './components/PhotoUpload';
import AlertSound from './components/AlertSound';
import ToastContainer from './components/ToastContainer';
import { useLanguage } from './LanguageContext';
import { getRiskZones, getSensorsLatest, getAlerts } from './api';

function App() {
  const { t } = useLanguage();
  const [riskZones, setRiskZones] = useState([]);
  const [sensors, setSensors] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [impacts, setImpacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('priority');

  useEffect(() => {
    fetchData();
    fetchPhotos();
    fetchImpacts();
    const interval = setInterval(() => {
      fetchData();
      fetchImpacts();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const zonesData = await getRiskZones();
      const sensorsData = await getSensorsLatest();
      const alertsData = await getAlerts();
      
      setRiskZones(zonesData || { type: 'FeatureCollection', features: [] });
      setSensors(Array.isArray(sensorsData) ? sensorsData : []);
      setAlerts(Array.isArray(alertsData) ? alertsData : []);
      setError(null);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch:', err);
      setError('Backend unreachable');
      setLoading(false);
    }
  };

  const fetchPhotos = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/photos');
      const data = await res.json();
      setPhotos(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch photos:', err);
    }
  };

  const fetchImpacts = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/impact-zones');
      const data = await res.json();
      setImpacts(data.zones || []);
    } catch (err) {
      console.error('Failed to fetch impacts:', err);
    }
  };

  const handlePhotoUploaded = (newPhoto) => {
    console.log('New photo uploaded:', newPhoto);
    fetchPhotos();
  };

  // Count critical alerts for badge
  const criticalCount = alerts.filter(a => 
    (a.severity || '').toLowerCase().includes('critical')
  ).length;

  const renderActiveView = () => {
    switch (activeView) {
      case 'priority': return <PriorityZones />;
      case 'alerts': return <AlertsPanel alerts={alerts} />;
      case 'roads': return <RoadStatus />;
      case 'weather': return <WeatherForecast />;
      case 'legend': return <Legend />;
      case 'system': return <SystemStatus sensors={sensors} />;
      default: return <PriorityZones />;
    }
  };

  if (loading) return <div className="loading-screen">🌄 Loading...</div>;
  if (error) return <div className="error-banner">⚠️ {error}</div>;

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">🏔️</span>
            <span className="logo-text">{t('app_title')}</span>
          </div>
          <span className="header-badge">{t('live')}</span>
        </div>
        <div className="header-right">
          <AlertSound alerts={alerts} criticalCount={criticalCount} />
          <FeaturesMenu activeView={activeView} setActiveView={setActiveView} />
          <LanguageToggle />
          <span className="header-time">{new Date().toLocaleString()}</span>
        </div>
      </header>

      {/* WhatsApp-style floating toast notifications */}
      <ToastContainer alerts={alerts} />

      <div className="dashboard-grid">
        <div className="map-section">
          <RiskMap 
            zones={riskZones} 
            sensors={sensors} 
            photos={photos} 
            impacts={impacts}
          />
          <PhotoUpload onUploaded={handlePhotoUploaded} />
        </div>

        <div className="sidebar">
          {renderActiveView()}
        </div>
      </div>

      <footer className="app-footer">
        <span>🌐 {t('data_source')}</span>
        <span>🔒 {t('secure')} • v2.0</span>
      </footer>
    </div>
  );
}

export default App;