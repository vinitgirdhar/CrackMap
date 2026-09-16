"use client";

import { STAGE_META, STAGE_ORDER } from "@/lib/civic";
import type { CaseStatus, PipelineStats } from "@/lib/types";

interface StageRailProps {
  stats: PipelineStats | null;
  activeFilter: CaseStatus | "ALL";
  onFilterChange: (filter: CaseStatus | "ALL") => void;
}

/**
 * The pipeline itself, drawn as a rail.
 *
 * Each node carries a live count, so the board reads as a system with work
 * flowing through it rather than a static list of steps. Nodes with cases in
 * them pulse; clicking one filters the case board below.
 */
export function StageRail({ stats, activeFilter, onFilterChange }: StageRailProps) {
  const counts = stats?.stage_counts ?? {};
  const total = stats?.total_cases ?? 0;

  return (
    <div className="stage-rail-wrap">
      <div className="stage-rail-head">
        <button
          type="button"
          className={`stage-rail-all${activeFilter === "ALL" ? " is-active" : ""}`}
          onClick={() => onFilterChange("ALL")}
        >
          All cases<span>{total}</span>
        </button>
        <p className="stage-rail-note">
          Stages with no button advance on their own — the portal acknowledges, the crew mobilises,
          the repair finishes.
        </p>
      </div>

      <div className="stage-rail" role="tablist" aria-label="Pipeline stages">
        {STAGE_ORDER.map((stage, index) => {
          const meta = STAGE_META[stage];
          const count = counts[stage] ?? 0;
          const isActive = activeFilter === stage;
          const autoStage = stage === "SUBMITTED" || stage === "WORK_ORDERED" || stage === "IN_REPAIR";

          return (
            <button
              key={stage}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`stage-node${isActive ? " is-active" : ""}${count > 0 ? " has-cases" : ""}`}
              style={{ "--stage-color": meta.color } as React.CSSProperties}
              onClick={() => onFilterChange(isActive ? "ALL" : stage)}
              title={`${meta.label} — owned by ${meta.owner}`}
            >
              <span className="stage-node-index">{index + 1}</span>
              <span className="stage-node-body">
                <span className="stage-node-label">{meta.short}</span>
                <span className="stage-node-owner">
                  {autoStage ? "auto" : meta.owner.split(" ")[0].toLowerCase()}
                </span>
              </span>
              <span className="stage-node-count">{count}</span>
              {count > 0 && <span className="stage-node-pulse" aria-hidden />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
