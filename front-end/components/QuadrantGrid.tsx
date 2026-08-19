import { ArrowUpRight, Zap, Database } from "lucide-react";
import type { DashboardSummary } from "@/lib/types";
import { computeMicroBars, severityLevel } from "@/lib/equalizer";

interface QuadrantGridProps {
  summary: DashboardSummary | null;
}

const SEVERITY_COPY: Record<string, { label: string; color: string }> = {
  low: { label: "Routine Maintenance Level", color: "#16a34a" },
  medium: { label: "Maintenance Recommended", color: "#eab308" },
  high: { label: "Priority Resurfacing Required", color: "#ef4444" },
};

function ArrowBadge() {
  return (
    <div className="circle-arrow-link" style={{ width: 28, height: 28 }}>
      <ArrowUpRight size={14} />
    </div>
  );
}

export function QuadrantGrid({ summary }: QuadrantGridProps) {
  const severity = summary ? SEVERITY_COPY[severityLevel(summary.avg_severity)] : null;
  const bars = computeMicroBars(summary?.class_distribution ?? {});

  return (
    <div className="quadrant-grid">
      <div className="pastel-card sage">
        <div className="pastel-card-top">
          <span className="pastel-title">Average Severity</span>
          <ArrowBadge />
        </div>
        <div>
          <div className="pastel-number">
            {summary ? summary.avg_severity : "--"}
            <span className="pastel-unit"> /defect</span>
          </div>
          {severity && (
            <div className="pastel-sublabel" style={{ color: severity.color }}>
              {severity.label}
            </div>
          )}
        </div>
      </div>

      <div className="pastel-card peach">
        <div className="pastel-card-top">
          <span className="pastel-title">Defect Distribution</span>
          <ArrowBadge />
        </div>
        <div className="micro-bar-chart">
          {bars.map((bar) => (
            <div className="bar-col" key={bar.code}>
              <div
                className="bar-fill"
                style={{
                  height: `${bar.pct}%`,
                  background: bar.code === "D40" ? "#22c55e" : bar.code === "D20" ? "#60a5fa" : "#cbd5e1",
                }}
              />
              <span className="bar-tag">{bar.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="pastel-card sky">
        <div className="pastel-card-top">
          <span className="pastel-title">Composite Damage Score</span>
          <ArrowBadge />
        </div>
        <div>
          <div className="pastel-number">
            {summary ? summary.composite_damage_score : "--"}
            <span className="pastel-unit"> /100</span>
          </div>
          <div className="pastel-sublabel" style={{ color: "#2563eb" }}>
            <Zap size={12} />
            Frame-Coverage Heuristic
          </div>
        </div>
      </div>

      <div className="pastel-card ice">
        <div className="pastel-card-top">
          <span className="pastel-title">Training Benchmark</span>
          <ArrowBadge />
        </div>
        <div>
          <div className="pastel-number">
            {summary?.total_images ?? 665}
            <span className="pastel-unit"> frames</span>
          </div>
          <div className="pastel-sublabel">
            <Database size={12} style={{ display: "inline", marginRight: 4 }} />
            Single-Class Pothole Detector
          </div>
        </div>
      </div>
    </div>
  );
}
