"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  Building2,
  Clock,
  HardHat,
  Loader2,
  MapPin,
  Radio,
  ShieldAlert,
  X,
} from "lucide-react";
import {
  awardCase,
  closeCase,
  getCase,
  submitCase,
  tenderCase,
  verifyCase,
} from "@/lib/api";
import {
  PRIORITY_COLOR,
  SLA_COLOR,
  SLA_LABEL,
  STAGE_META,
  STAGE_ORDER,
  formatClock,
  formatInr,
  formatSlaRemaining,
  liveRepairProgress,
  nextStep,
  simDaysSince,
} from "@/lib/civic";
import { useNow } from "@/lib/hooks/useNow";
import type { CaseView } from "@/lib/types";
import { AuditTimeline } from "./AuditTimeline";
import { BidTable } from "./BidTable";
import { BoqTable } from "./BoqTable";
import { DeliverablesRow } from "./DeliverablesRow";
import { VerifyPanel } from "./VerifyPanel";

interface CaseDetailProps {
  caseId: number;
  onClose: () => void;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="kv-row">
      <span className="kv-label">{label}</span>
      <span className="kv-value">{children}</span>
    </div>
  );
}

export function CaseDetail({ caseId, onClose }: CaseDetailProps) {
  const [caseView, setCaseView] = useState<CaseView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const now = useNow(1000);
  // Award and re-inspection are performed inside their own sections further
  // down; the banner scrolls there rather than duplicating the control.
  const tenderRef = useRef<HTMLElement | null>(null);
  const verifyRef = useRef<HTMLElement | null>(null);

  const load = useCallback(async () => {
    try {
      setCaseView(await getCase(caseId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this case");
    }
  }, [caseId]);

  // Poll: the clock-driven stages move while the drawer is open.
  useEffect(() => {
    // The first poll is queued rather than run inline, so state only ever
    // changes from a callback the external system drives — never from the
    // effect body itself (React compiler lint), and a mount renders once.
    const first = setTimeout(load, 0);
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void load();
    }, 2500);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [load]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const runAction = useCallback(
    async (fn: () => Promise<CaseView>) => {
      setBusy(true);
      setError(null);
      try {
        setCaseView(await fn());
        window.dispatchEvent(new CustomEvent("crackmap:refresh"));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Action failed");
      } finally {
        setBusy(false);
      }
    },
    []
  );

  if (!caseView) {
    return (
      <div className="case-drawer-overlay" onClick={onClose}>
        <aside className="case-drawer" onClick={(e) => e.stopPropagation()}>
          <div className="civic-empty">
            {error ? <ShieldAlert size={22} /> : <Loader2 size={22} className="spin-animation" />}
            <p>{error ?? "Loading case…"}</p>
          </div>
        </aside>
      </div>
    );
  }

  const meta = STAGE_META[caseView.status];
  const step = nextStep(caseView);
  const progress = liveRepairProgress(caseView, now);
  const stageIdx = STAGE_ORDER.indexOf(caseView.status);

  async function handleAction() {
    if (step.kind !== "action") return;
    if (step.action === "submit") return runAction(() => submitCase(caseView!.id));
    if (step.action === "tender") return runAction(() => tenderCase(caseView!.id));
    if (step.action === "close") return runAction(() => closeCase(caseView!.id));
  }

  return (
    <div className="case-drawer-overlay" onClick={onClose}>
      <aside
        className="case-drawer"
        style={{ "--stage-color": meta.color } as React.CSSProperties}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={`Case ${caseView.id}`}
      >
        <header className="case-drawer-head">
          <div>
            <div className="case-drawer-title">
              <h3>Case #{caseView.id}</h3>
              <span
                className="civic-pill"
                style={{
                  color: PRIORITY_COLOR[caseView.priority ?? "P4"],
                  borderColor: PRIORITY_COLOR[caseView.priority ?? "P4"],
                }}
              >
                {caseView.priority} · {caseView.priority_label}
              </span>
              <span className="case-drawer-stage">{meta.label}</span>
            </div>
            <p className="case-drawer-sub">
              Opened {formatClock(caseView.created_at)} · {caseView.findings.length} finding(s) ·{" "}
              {caseView.total_potholes} pothole(s) · {caseView.patch_area_m2 ?? 0} m²
            </p>
          </div>
          <button type="button" className="popover-icon-btn" onClick={onClose} aria-label="Close case">
            <X size={16} />
          </button>
        </header>

        {/* Stage progress strip */}
        <div className="case-stage-strip">
          {STAGE_ORDER.map((stage, i) => (
            <span
              key={stage}
              className={`case-stage-dot${i < stageIdx ? " past" : ""}${i === stageIdx ? " current" : ""}`}
              style={{ "--stage-color": STAGE_META[stage].color } as React.CSSProperties}
              title={STAGE_META[stage].label}
            />
          ))}
          <span className="case-stage-strip-label">
            step {stageIdx + 1} of {STAGE_ORDER.length}
          </span>
        </div>

        {/* What happens next */}
        <div className={`next-step-banner kind-${step.kind}`}>
          <div className="next-step-text">
            <strong>{step.label}</strong>
            <span>{step.hint}</span>
          </div>
          {step.kind === "action" && step.action !== "verify" && step.action !== "award" && (
            <button type="button" className="primary-pill-btn" disabled={busy} onClick={handleAction}>
              {busy && <Loader2 size={15} className="spin-animation" />}
              {step.action === "submit" && "File now"}
              {step.action === "tender" && "Float tender"}
              {step.action === "close" && "Close & certify"}
            </button>
          )}
          {step.kind === "action" && (step.action === "award" || step.action === "verify") && (
            <button
              type="button"
              className="primary-pill-btn"
              onClick={() =>
                (step.action === "award" ? tenderRef : verifyRef).current?.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                })
              }
            >
              <ArrowDown size={15} />
              {step.action === "award" ? "Compare bids" : "Upload after-photo"}
            </button>
          )}
          {step.kind === "waiting" && (
            <span className="waiting-badge">
              <Radio size={13} className="pulse-icon" />
              {caseView.status === "SUBMITTED"
                ? `${simDaysSince(caseView.submitted_at, now, caseView.seconds_per_sim_day).toFixed(1)} sim-days at the portal`
                : `${progress.toFixed(0)}% complete`}
            </span>
          )}
        </div>

        {step.kind === "waiting" && caseView.awarded && (
          <div className="repair-progress-block">
            <div className="case-progress-track lg">
              <div className="case-progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="repair-progress-meta">
              <span>
                <HardHat size={13} /> {caseView.awarded.contractor_name} ·{" "}
                {caseView.awarded.crew_count}-person crew
              </span>
              <span>
                day {Math.min(
                  caseView.awarded.promised_days ?? 1,
                  Math.max(0, simDaysSince(caseView.awarded.awarded_at, now, caseView.seconds_per_sim_day) - 1)
                ).toFixed(1)}{" "}
                of {caseView.awarded.promised_days?.toFixed(0)}
              </span>
            </div>
          </div>
        )}

        {error && <p className="batch-status error">{error}</p>}

        {/* Filing record */}
        <section className="case-section">
          <h4>
            <Building2 size={16} /> Municipal filing record
            {caseView.portal && <span className="sim-badge">simulated filing</span>}
          </h4>
          {caseView.portal ? (
            <div className="kv-grid">
              <Row label="Authority">{caseView.portal.authority}</Row>
              <Row label="Portal">
                <a href={caseView.portal.portal_url} target="_blank" rel="noreferrer">
                  {caseView.portal.name}
                </a>
              </Row>
              <Row label="Department">{caseView.portal.department}</Row>
              <Row label="Grievance no.">
                <code>{caseView.tracking_id}</code>
              </Row>
              <Row label="Assigned officer">{caseView.officer ?? "Pending acknowledgement"}</Row>
              <Row label="Routing basis">{caseView.routing_note}</Row>
              <Row label="Filed">{formatClock(caseView.submitted_at)}</Row>
              <Row label="Acknowledged">{formatClock(caseView.acknowledged_at)}</Row>
              <Row label="Response window">
                <span style={{ color: SLA_COLOR[caseView.sla_state], fontWeight: 700 }}>
                  <Clock size={12} /> {SLA_LABEL[caseView.sla_state]}
                </span>{" "}
                — {formatSlaRemaining(caseView, now)}
              </Row>
            </div>
          ) : (
            <p className="civic-subtle">
              Still a draft. Filing routes it by coordinate to the authority that owns this road and mints
              a grievance number in that authority&rsquo;s own format.
            </p>
          )}
          <p className="civic-footnote">
            CrackMap models municipal intake behaviour — grievance number format, owning department,
            acknowledgement lag and statutory response window. Nothing is transmitted to any external
            authority.
          </p>
        </section>

        {/* Evidence */}
        <section className="case-section">
          <h4>
            <MapPin size={16} /> Photographic evidence
          </h4>
          <div className="evidence-grid">
            {caseView.findings.map((finding) => (
              <article className="evidence-card" key={finding.id}>
                {finding.annotated_image ? (
                  // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
                  <img src={finding.annotated_image} alt={`Detections at ${finding.road_name}`} />
                ) : (
                  <div className="evidence-placeholder">no frame stored</div>
                )}
                <div className="evidence-body">
                  <strong>{finding.road_name}</strong>
                  <span className="civic-subtle">{finding.address ?? "address not resolved"}</span>
                  <div className="evidence-stats">
                    <span>{finding.total_defects} potholes</span>
                    <span>severity {finding.severity_score}/5</span>
                    <span>{finding.road_class} road</span>
                    <span>
                      {finding.lat !== null && finding.lon !== null
                        ? `${finding.lat.toFixed(5)}, ${finding.lon.toFixed(5)}`
                        : "no coordinate"}
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        {/* Tender */}
        {caseView.bids.length > 0 && (
          <section className="case-section" ref={tenderRef}>
            <h4>Tender — {caseView.bids.length} bids</h4>
            <BidTable
              bids={caseView.bids}
              estimateInr={caseView.estimate_inr}
              awardedContractorId={caseView.awarded?.contractor_id ?? null}
              onAward={
                caseView.status === "TENDERED"
                  ? (contractorId) => runAction(() => awardCase(caseView.id, contractorId))
                  : undefined
              }
            />
          </section>
        )}

        {/* Contract */}
        {caseView.awarded && (
          <section className="case-section">
            <h4>
              <HardHat size={16} /> Repair contract
            </h4>
            <div className="kv-grid">
              <Row label="Contractor">
                {caseView.awarded.contractor_name}{" "}
                <span className="civic-subtle-inline">({caseView.awarded.specialty})</span>
              </Row>
              <Row label="Rating / crew">
                {caseView.awarded.rating.toFixed(1)}/5 · {caseView.awarded.crew_count} people
              </Row>
              <Row label="Contract value">
                {formatInr(caseView.awarded.awarded_inr)}{" "}
                <span
                  className="civic-subtle-inline"
                  style={{ color: caseView.awarded.variance_pct <= 0 ? "#16a34a" : "#ef4444" }}
                >
                  ({caseView.awarded.variance_pct > 0 ? "+" : ""}
                  {caseView.awarded.variance_pct.toFixed(1)}% vs estimate)
                </span>
              </Row>
              <Row label="Promised duration">{caseView.awarded.promised_days?.toFixed(0)} day(s)</Row>
              <Row label="Work order issued">{formatClock(caseView.awarded.awarded_at)}</Row>
              <Row label="Repair completed">{formatClock(caseView.repaired_at)}</Row>
            </div>
          </section>
        )}

        {/* Re-inspection */}
        {(caseView.status === "REPAIRED" || caseView.verification) && (
          <section className="case-section" ref={verifyRef}>
            <h4>AI re-inspection</h4>
            <VerifyPanel
              caseView={caseView}
              onVerify={async (file) => {
                await runAction(() => verifyCase(caseView.id, file));
              }}
            />
          </section>
        )}

        {/* Costing */}
        {caseView.boq && (
          <section className="case-section">
            <h4>Bill of quantities — bituminous pothole repair</h4>
            <BoqTable boq={caseView.boq} />
          </section>
        )}

        {/* Audit trail */}
        <section className="case-section">
          <h4>Audit trail</h4>
          <AuditTimeline events={caseView.events} now={now} />
        </section>

        {/* Deliverables */}
        <section className="case-section">
          <h4>Deliverables</h4>
          <DeliverablesRow caseView={caseView} />
        </section>
      </aside>
    </div>
  );
}
