// api.js
// Configurable API base URL — point this at your backend.
// During dev with the backend running locally, this default is correct.
export const API_BASE_URL = "http://localhost:8000";

async function fetchJson(path) {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
  }
  return res.json();
}

export function getRiskZones() {
  return fetchJson("/api/risk-zones");
}

export function getSensorsLatest() {
  return fetchJson("/api/sensors/latest");
}

export function getSensorHistory(nodeId, hours = 24) {
  return fetchJson(`/api/sensors/${nodeId}/history?hours=${hours}`);
}

export function getAlerts(limit = 20) {
  return fetchJson(`/api/alerts?limit=${limit}`);
}