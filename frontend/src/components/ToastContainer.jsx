import { useEffect, useState } from 'react';
import ToastNotification from './ToastNotification';

const ToastContainer = ({ alerts = [] }) => {
  const [toasts, setToasts] = useState([]);
  const [seenAlertIds, setSeenAlertIds] = useState(new Set());

  useEffect(() => {
    if (!alerts || alerts.length === 0) return;

    const newAlerts = alerts.filter(
      (a) => !seenAlertIds.has(a.alert_id)
    );

    if (newAlerts.length === 0) return;

    const toShow = newAlerts.slice(0, 3);

    setToasts((prev) => {
      const combined = [...toShow, ...prev];
      return combined.slice(0, 3);
    });

    setSeenAlertIds((prev) => {
      const newSet = new Set(prev);
      toShow.forEach((a) => newSet.add(a.alert_id));
      return newSet;
    });

  }, [alerts, seenAlertIds]);

  const removeToast = (alertId) => {
    setToasts((prev) => prev.filter((t) => t.alert_id !== alertId));
  };

  if (toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <ToastNotification
          key={toast.alert_id}
          alert={toast}
          onClose={() => removeToast(toast.alert_id)}
          duration={5000}
        />
      ))}
    </div>
  );
};

export default ToastContainer;