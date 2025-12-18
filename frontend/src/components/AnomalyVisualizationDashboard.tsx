import React from "react";
import AnomalyChart from "./AnomalyChart";

export type Anomaly = {
  name: string;
  anomaly_type: string;
  event_hour?: string | number | null;
  clicks?: number | null;
  avg_clicks?: number | null;
};

export type ChartPoint = {
  hour: string;
  clicks: number;
  baseline?: number | null;
  source?: string;
  type?: string;
};

export type Stats = {
  total: number;
  spike_count: number;
  drop_count: number;
  max_deviation?: number;
};

interface Props {
  chartData?: ChartPoint[];
  anomalies?: Anomaly[];
  stats?: Partial<Stats>;
  title?: string;
  chartConfig?: { height?: number };
}

const AnomalyVisualizationDashboard: React.FC<Props> = ({
  chartData = [],
  anomalies = [],
  stats,
  title = "Anomaly Visualization",
  chartConfig = {}
}) => {
  const computedStats: Stats = {
    total: stats?.total ?? anomalies.length,
    spike_count: stats?.spike_count ?? anomalies.filter((a) => a.anomaly_type === "click_spike").length,
    drop_count: stats?.drop_count ?? anomalies.filter((a) => a.anomaly_type === "click_drop").length,
    max_deviation: stats?.max_deviation ?? 0
  };

  return (
    <div
      style={{
        padding: "24px",
        background: "#ffffff",
        borderRadius: "20px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
        maxWidth: "100%",
        width: "100%",
        boxSizing: "border-box",
        overflow: "hidden"
      }}
    >
      <h2
        style={{
          margin: "0 0 20px 0",
          fontSize: "24px",
          fontWeight: 700,
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text"
        }}
      >
        {title}
      </h2>

      {/* Stats Cards */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          marginBottom: "24px",
          flexWrap: "wrap"
        }}
      >
        <div
          style={{
            flex: 1,
            minWidth: "150px",
            padding: "16px 20px",
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            borderRadius: "12px",
            color: "white",
            boxShadow: "0 4px 12px rgba(102, 126, 234, 0.3)"
          }}
        >
          <div style={{ fontSize: "14px", opacity: 0.9, marginBottom: 4 }}>
            סה״כ אנומליות
          </div>
          <div style={{ fontSize: "32px", fontWeight: 700 }}>
            {computedStats.total}
          </div>
        </div>

        <div
          style={{
            flex: 1,
            minWidth: "150px",
            padding: "16px 20px",
            background: "linear-gradient(135deg, #fc8181 0%, #f56565 100%)",
            borderRadius: "12px",
            color: "white",
            boxShadow: "0 4px 12px rgba(252, 129, 129, 0.3)"
          }}
        >
          <div style={{ fontSize: "14px", opacity: 0.9, marginBottom: 4 }}>
            ספייקים ⬆️
          </div>
          <div style={{ fontSize: "32px", fontWeight: 700 }}>
            {computedStats.spike_count}
          </div>
        </div>

        <div
          style={{
            flex: 1,
            minWidth: "150px",
            padding: "16px 20px",
            background: "linear-gradient(135deg, #4fd1c5 0%, #38b2ac 100%)",
            borderRadius: "12px",
            color: "white",
            boxShadow: "0 4px 12px rgba(79, 209, 197, 0.3)"
          }}
        >
          <div style={{ fontSize: "14px", opacity: 0.9, marginBottom: 4 }}>
            ירידות ⬇️
          </div>
          <div style={{ fontSize: "32px", fontWeight: 700 }}>
            {computedStats.drop_count}
          </div>
        </div>
      </div>

      <AnomalyChart data={chartData} anomalies={anomalies} config={chartConfig} />
    </div>
  );
};

export default AnomalyVisualizationDashboard;
