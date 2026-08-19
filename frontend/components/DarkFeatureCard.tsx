import { ArrowUpRight } from "lucide-react";
import type { DashboardSummary } from "@/lib/types";
import { computeEqualizerDots } from "@/lib/equalizer";

interface DarkFeatureCardProps {
  summary: DashboardSummary | null;
  lastRefreshed: Date | null;
  onExpand: () => void;
}

export function DarkFeatureCard({ summary, lastRefreshed, onExpand }: DarkFeatureCardProps) {
  const dots = computeEqualizerDots(summary?.potholes_count ?? 0, summary?.cracks_count ?? 0);

  return (
    <div className="dark-feature-card">
      <div>
        <div className="card-header-row">
          <div>
            <h3>Defect Matrix & Saliency</h3>
            <p>All Pavement Anomaly Layers (JRA Standards)</p>
          </div>
          <button className="circle-arrow-link" onClick={onExpand} type="button" aria-label="Open detector">
            <ArrowUpRight size={18} />
          </button>
        </div>

        <div className="dark-card-legend">
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#ef4444" }} />
            Active Hazards ({summary?.potholes_count ?? 0} Potholes)
          </span>
          <span className="legend-item">
            <span className="legend-dot" style={{ background: "#22c55e" }} />
            Cracks ({summary?.cracks_count ?? 0} Linears)
          </span>
        </div>

        <div className="dataset-info-strip">
          <span>
            Dataset: <strong>{summary?.dataset_name ?? "--"}</strong>
          </span>
          <span>
            Frames: <strong>{summary?.total_images ?? "--"}</strong>
          </span>
          {lastRefreshed && (
            <span>
              Updated: <strong>{lastRefreshed.toLocaleTimeString()}</strong>
            </span>
          )}
        </div>
      </div>

      <div className="dot-matrix-equalizer">
        {dots.map((state, i) => (
          <div
            key={i}
            className={`matrix-dot${state === "red" ? " active-red" : ""}${state === "teal" ? " active-teal" : ""}`}
          />
        ))}
      </div>
    </div>
  );
}
