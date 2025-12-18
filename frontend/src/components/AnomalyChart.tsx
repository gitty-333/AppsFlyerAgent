import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceDot,
  Legend
} from "recharts";
import type { ChartPoint, Anomaly } from "./AnomalyVisualizationDashboard";

interface Props {
  data?: ChartPoint[];
  anomalies?: Anomaly[];
  config?: { height?: number };
}

const formatHour = (v: any) => {
  if (!v) return "";
  const s = String(v);
  if (s.includes("T")) return s.slice(11, 16);
  return s;
};

// Custom Tooltip מעוצב
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;

  return (
    <div
      style={{
        background: "rgba(255, 255, 255, 0.98)",
        border: "1px solid #e0e0e0",
        borderRadius: "12px",
        padding: "12px 16px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.15)"
      }}
    >
      <p style={{ margin: 0, fontWeight: 600, color: "#333", marginBottom: 8 }}>
        {formatHour(label)}
      </p>
      {payload.map((entry: any, index: number) => (
        <p
          key={index}
          style={{
            margin: "4px 0",
            color: entry.color,
            fontSize: "14px",
            fontWeight: 500
          }}
        >
          <span style={{ opacity: 0.8 }}>{entry.name}:</span>{" "}
          <strong>{entry.value?.toLocaleString()}</strong>
        </p>
      ))}
    </div>
  );
};

const AnomalyChart: React.FC<Props> = ({ data = [], anomalies = [], config = {} }) => {
  return (
    <div
      style={{
        width: "100%",
        height: config.height ?? 400,
        background: "linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%)",
        borderRadius: "16px",
        padding: "20px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.08)"
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorClicks" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#667eea" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#667eea" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="colorBaseline" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#48bb78" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#48bb78" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" opacity={0.5} />
          
          <XAxis
            dataKey="hour"
            tickFormatter={formatHour}
            stroke="#718096"
            style={{ fontSize: "12px", fontWeight: 500 }}
          />
          
          <YAxis
            stroke="#718096"
            style={{ fontSize: "12px", fontWeight: 500 }}
            tickFormatter={(value) => value.toLocaleString()}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          <Legend
            wrapperStyle={{
              fontSize: "13px",
              fontWeight: 500,
              paddingTop: "10px"
            }}
          />

          {/* Area Chart for Clicks with gradient */}
          <Area
            type="natural"
            dataKey="clicks"
            stroke="#667eea"
            strokeWidth={3}
            fill="url(#colorClicks)"
            name="Clicks"
            animationDuration={1000}
          />

          {/* Baseline as dashed line */}
          <Line
            type="natural"
            dataKey="baseline"
            stroke="#48bb78"
            strokeWidth={2}
            strokeDasharray="8 4"
            dot={false}
            name="Baseline"
            animationDuration={1000}
          />

          {/* Anomaly markers */}
          {anomalies.map((a, i) => (
            <ReferenceDot
              key={i}
              x={String(a.event_hour ?? "")}
              y={a.clicks ?? 0}
              r={8}
              stroke={a.anomaly_type === "click_spike" ? "#fc8181" : "#4fd1c5"}
              strokeWidth={3}
              fill={a.anomaly_type === "click_spike" ? "#feb2b2" : "#9decf9"}
              isFront={true}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default AnomalyChart;
