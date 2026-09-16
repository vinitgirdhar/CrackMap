"use client";

import { Building2, Clock, HardHat, MapPin, ShieldCheck } from "lucide-react";
import {
  PRIORITY_COLOR,
  SLA_COLOR,
  STAGE_META,
  formatCompactInr,
  formatSlaRemaining,
  liveRepairProgress,
  nextStep,
} from "@/lib/civic";
import type { CaseView } from "@/lib/types";

interface CaseCardProps {
  caseView: CaseView;
  now: number;
  isSelected: boolean;
  onOpen: (caseId: number) => void;
}

export function CaseCard({ caseView, now, isSelected, onOpen }: CaseCardProps) {
  const meta = STAGE_META[caseView.status];
  const step = nextStep(caseView);
  const progress = liveRepairProgress(caseView, now);
  const roads = caseView.findings.map((f) => f.road_name);
  const roadLabel = roads.length > 1 ? `${roads[0]} +${roads.length - 1} more` : roads[0] ?? "Unlocated";
  const showProgress = caseView.status === "WORK_ORDERED" || caseView.status === "IN_REPAIR";

  return (
    <button
      type="button"
      className={`case-card${isSelected ? " is-selected" : ""}`}
      style={{ "--stage-color": meta.color } as React.CSSProperties}
      onClick={() => onOpen(caseView.id)}
    >
      <div className="case-card-top">
        <span className="case-card-id">Case #{caseView.id}</span>
        <span
          className="civic-pill"
          style={{
            color: PRIORITY_COLOR[caseView.priority ?? "P4"],
            borderColor: PRIORITY_COLOR[caseView.priority ?? "P4"],
          }}
        >
          {caseView.priority ?? "—"}
        </span>
        <span className="case-card-stage">{meta.short}</span>
      </div>

      <div className="case-card-road">
        <MapPin size={14} />
        <span>{roadLabel}</span>
      </div>

      <div className="case-card-portal">
        {caseView.portal ? (
          <>
            <Building2 size={13} />
            <span title={caseView.portal.name}>{caseView.portal.authority}</span>
            <code>{caseView.tracking_id}</code>
          </>
        ) : (
          <>
            <Building2 size={13} />
            <span className="civic-subtle-inline">Not filed with any authority yet</span>
          </>
        )}
      </div>

      {showProgress && (
        <div className="case-card-progress">
          <div className="case-progress-track">
            <div className="case-progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <span>
            <HardHat size={12} /> {caseView.awarded?.contractor_name?.split(" ")[0] ?? "Crew"} ·{" "}
            {progress.toFixed(0)}%
          </span>
        </div>
      )}

      {caseView.verification && (
        <div className={`case-card-verify${caseView.verification.passed ? " passed" : " failed"}`}>
          <ShieldCheck size={12} />
          {caseView.verification.passed
            ? `Re-inspection passed · ${caseView.verification.effectiveness_pct.toFixed(0)}% cleared`
            : `Rework — ${caseView.verification.defects_after} defect(s) still detected`}
        </div>
      )}

      <div className="case-card-metrics">
        <span>
          <strong>{caseView.total_potholes}</strong> potholes
        </span>
        <span>
          <strong>{caseView.patch_area_m2 ?? 0}</strong> m²
        </span>
        <span>
          <strong>
            {caseView.awarded?.awarded_inr
              ? formatCompactInr(caseView.awarded.awarded_inr)
              : formatCompactInr(caseView.estimate_inr)}
          </strong>{" "}
          {caseView.awarded?.awarded_inr ? "contract" : "est."}
        </span>
      </div>

      <div className="case-card-foot">
        <span className="case-card-sla" style={{ color: SLA_COLOR[caseView.sla_state] }}>
          <Clock size={12} /> {formatSlaRemaining(caseView, now)}
        </span>
        <span className={`case-card-step kind-${step.kind}`}>{step.label}</span>
      </div>
    </button>
  );
}
