import type { DashboardSummary } from "@/lib/types";

interface HeroSectionProps {
  summary: DashboardSummary | null;
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="metric-item">
      <span className="metric-label">{label}</span>
      <span className="metric-number">
        {value}
        <sup>{unit}</sup>
      </span>
    </div>
  );
}

export function HeroSection({ summary }: HeroSectionProps) {
  return (
    <div className="hero-section">
      <div className="hero-title-group">
        <span className="hero-sub">Single-Class Pothole Detector</span>
        <h1 className="hero-main">Pavement Inspection AI</h1>
      </div>
      <div className="hero-metrics-row">
        <Metric
          label="Training Corpus"
          value={summary ? summary.total_images.toLocaleString() : "665"}
          unit="imgs"
        />
        <Metric
          label="Dataset Potholes"
          value={summary ? summary.total_defects.toLocaleString() : "1,739"}
          unit="boxes"
        />
        <Metric label="Model Backbone" value="YOLOv8s" unit="v8" />
        <Metric label="Target Classes" value="1" unit="pothole" />
      </div>
    </div>
  );
}
