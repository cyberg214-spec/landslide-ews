// components/SensorPopupChart.jsx
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { getSensorHistory } from "../api";

export default function SensorPopupChart({ nodeId }) {
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSensorHistory(nodeId, 24)
      .then(setHistory)
      .catch((e) => setError(e.message));
  }, [nodeId]);

  if (error) return <div style={{ fontSize: 12, color: "#f87171" }}>Couldn't load history</div>;
  if (!history) return <div style={{ fontSize: 12 }}>Loading…</div>;

  const chartData = history.map((h, i) => ({
    idx: i,
    soil_moisture: h.soil_moisture,
    pore_water_pressure: h.pore_water_pressure,
    risk_score: h.risk_score,
  }));

  return (
    <div style={{ width: 220 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{nodeId}</div>
      <ResponsiveContainer width="100%" height={100}>
        <LineChart data={chartData}>
          <XAxis dataKey="idx" hide />
          <YAxis hide domain={[0, 100]} />
          <Tooltip />
          <Line type="monotone" dataKey="soil_moisture" stroke="#38bdf8" dot={false} strokeWidth={2} name="Soil Moisture" />
          <Line type="monotone" dataKey="pore_water_pressure" stroke="#a78bfa" dot={false} strokeWidth={2} name="Pore Pressure" />
        </LineChart>
      </ResponsiveContainer>
      <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>
        Blue: soil moisture · Purple: pore pressure
      </div>
    </div>
  );
}
