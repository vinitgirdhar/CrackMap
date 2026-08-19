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
        <span className="hero-sub">Road Health Intelligence</span>
        <h1 className="hero-main">Pavement Inspection AI</h1>
      </div>
      <div className="hero-metrics-row">
        <Metric
          label="Surveyed Area"
          value={summary ? summary.surveyed_area_m2.toLocaleString() : "--"}
          unit="m²"
        />
        <Metric
          label="Verified Pavement"
          value={summary ? summary.verified_pavement_m2.toLocaleString() : "--"}
          unit="m²"
        />
        <Metric label="Active Hazards" value={summary ? String(summary.total_defects) : "--"} unit="pts" />
        <Metric label="Survey Frames" value={summary ? String(summary.total_images) : "--"} unit="imgs" />
      </div>
    </div>
  );
}
