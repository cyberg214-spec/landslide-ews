import { useEffect, useRef, useState } from 'react';

const AlertSound = ({ alerts = [], criticalCount = 0 }) => {
  const [muted, setMuted] = useState(() => {
    return localStorage.getItem('alert_muted') === 'true';
  });
  const [lastAlertId, setLastAlertId] = useState(null);
  const audioCtxRef = useRef(null);

  // Initialize audio context
  const getAudioCtx = () => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioCtxRef.current;
  };

  // Play beep sound using Web Audio API (no file needed!)
  const playBeep = (severity = 'critical') => {
    try {
      const ctx = getAudioCtx();
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const isCritical = severity === 'critical';
      const beepCount = isCritical ? 4 : 2;
      const frequency = isCritical ? 880 : 660;
      const duration = isCritical ? 0.25 : 0.2;
      const gap = 0.15;

      for (let i = 0; i < beepCount; i++) {
        const startTime = ctx.currentTime + i * (duration + gap);
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.value = frequency;

        gain.gain.setValueAtTime(0.3, startTime);
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(startTime);
        osc.stop(startTime + duration);
      }
    } catch (err) {
      console.error('Sound play failed:', err);
    }
  };

  // ================================================================
  // PART 5: Poll backend for new critical alerts
  // ================================================================
  useEffect(() => {
    const checkAlerts = async () => {
      if (muted) return;
      try {
        const res = await fetch('http://localhost:8000/api/alerts');
        const data = await res.json();

        const criticalAlerts = data.filter(a => {
          const sev = (a.severity || '').toLowerCase();
          return sev.includes('critical');
        });

        if (criticalAlerts.length === 0) return;

        const latest = criticalAlerts[0];
        if (latest.alert_id === lastAlertId) return;

        setLastAlertId(latest.alert_id);
        playBeep('critical');

        // Browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('🚨 LANDSLIDE ALERT', {
            body: `${latest.location_name || 'Unknown'}: ${latest.message}`,
            icon: '/favicon.ico',
            requireInteraction: true,
          });
        }
      } catch (err) {
        console.error('Alert check failed:', err);
      }
    };

    // Check every 5 seconds
    const interval = setInterval(checkAlerts, 5000);
    checkAlerts(); // Immediate first check

    return () => clearInterval(interval);
  }, [muted, lastAlertId]);

  // Ask for notification permission on mount
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Save mute preference
  useEffect(() => {
    localStorage.setItem('alert_muted', muted);
  }, [muted]);

  return (
    <button
      className={`alert-sound-btn ${muted ? 'muted' : 'active'}`}
      onClick={() => setMuted(!muted)}
      title={muted ? 'Unmute alerts' : 'Mute alerts'}
    >
      {muted ? '🔇' : '🔔'}
      {criticalCount > 0 && !muted && (
        <span className="alert-sound-badge">{criticalCount}</span>
      )}
    </button>
  );
};

export default AlertSound;