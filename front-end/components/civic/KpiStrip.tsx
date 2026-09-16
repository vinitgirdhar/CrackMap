"use client";

import {
  AlertTriangle,
  BadgeCheck,
  Banknote,
  FolderOpen,
  MapPinned,
  Ruler,
} from "lucide-react";
import { formatCompactInr } from "@/lib/civic";
import type { PipelineStats } from "@/lib/types";

interface KpiStripProps {
  stats: PipelineStats | null;
}

function Tile({
  icon,
  label,
  value,
  sub,
  tone = "neutral",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  tone?: "neutral" | "good" | "warn" | "bad";
}) {
  return (
    <div className={`civic-kpi tone-${tone}`}>
      <span className="civic-kpi-icon">{icon}</span>
      <div className="civic-kpi-body">
        <span className="civic-kpi-label">{label}</span>
        <span className="civic-kpi-value">{value}</span>
        <span className="civic-kpi-sub">{sub}</span>
      </div>
    </div>
  );
}

export function KpiStrip({ stats }: KpiStripProps) {
  if (!stats) {
    return (
      <div className="civic-kpi-strip">
        {Array.from({ length: 6 }).map((_, i) => (
          <div className="civic-kpi is-skeleton" key={i} />
        ))}
      </div>
    );
  }

  const repairRate =
    stats.potholes_reported > 0
      ? Math.round((stats.potholes_repaired / stats.potholes_reported) * 100)
      : 0;

  return (
    <div className="civic-kpi-strip">
      <Tile
        icon={<MapPinned size={17} />}
        label="Findings logged"
        value={String(stats.total_findings)}
        sub={`${stats.unassigned_findings} awaiting a case`}
      />
      <Tile
        icon={<FolderOpen size={17} />}
        label="Open cases"
        value={String(stats.open_cases)}
        sub={`${stats.closed_cases} closed of ${stats.total_cases}`}
      />
      <Tile
        icon={<AlertTriangle size={17} />}
        label="SLA pressure"
        value={String(stats.sla_breached + stats.sla_at_risk)}
        sub={`${stats.sla_breached} breached · ${stats.sla_at_risk} at risk`}
        tone={stats.sla_breached > 0 ? "bad" : stats.sla_at_risk > 0 ? "warn" : "good"}
      />
      <Tile
        icon={<BadgeCheck size={17} />}
        label="Potholes repaired"
        value={`${stats.potholes_repaired}/${stats.potholes_reported}`}
        sub={`${repairRate}% verified fixed`}
        tone={repairRate >= 50 ? "good" : "neutral"}
      />
      <Tile
        icon={<Ruler size={17} />}
        label="Carriageway logged"
        value={`${stats.area_m2_reported} m²`}
        sub="estimated patch footprint"
      />
      <Tile
        icon={<Banknote size={17} />}
        label="Committed spend"
        value={formatCompactInr(stats.committed_inr)}
        sub={`${formatCompactInr(stats.estimated_inr)} estimated`}
      />
    </div>
  );
}
