"use client";

import {
  Banknote,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  HardHat,
  MapPin,
  ShieldCheck,
  Star,
  Users,
} from "lucide-react";
import { formatClock, formatInr } from "@/lib/civic";
import type { CompletedRepair } from "@/lib/types";

/**
 * One finished job, laid out the way a municipal completion file would be:
 * the before/after evidence first, then what it cost and who did it, then the
 * contractor's own handover notice. Everything here is visible on load — this
 * is a record to read, not a drill-down to click into.
 */
export function CompletedRepairCard({ repair }: { repair: CompletedRepair }) {
  const onTime = repair.actual_days <= repair.promised_days;
  const otherRoads = repair.roads.length - 1;

  return (
    <article className="completed-card">
      <header className="completed-card-head">
        <div className="completed-card-title">
          <MapPin size={15} />
          <h5>{repair.primary_road}</h5>
          {otherRoads > 0 && <span className="completed-more-roads">+{otherRoads} more</span>}
        </div>
        <div className="completed-card-badges">
          {repair.priority && (
            <span className="completed-priority-pill">{repair.priority}</span>
          )}
          <span className="completed-verified-pill">
            <ShieldCheck size={12} /> Verified {repair.effectiveness_pct.toFixed(0)}% cleared
          </span>
        </div>
      </header>

      {repair.address && <p className="completed-address">{repair.address}</p>}

      {/* Before / after evidence — the thing this whole section exists for */}
      <div className="completed-evidence">
        <div className="completed-evidence-pane">
          <span className="completed-evidence-tag before">Before</span>
          {repair.before_image ? (
            // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
            <img src={repair.before_image} alt={`${repair.primary_road} before repair`} />
          ) : (
            <div className="completed-evidence-placeholder">No frame stored</div>
          )}
          <span className="completed-evidence-caption">{repair.potholes_before} pothole(s) detected</span>
        </div>
        <div className="completed-evidence-pane">
          <span className="completed-evidence-tag after">After</span>
          {repair.after_image ? (
            // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
            <img src={repair.after_image} alt={`${repair.primary_road} after repair`} />
          ) : (
            <div className="completed-evidence-placeholder">No frame stored</div>
          )}
          <span className="completed-evidence-caption">{repair.potholes_after} pothole(s) remaining</span>
        </div>
      </div>

      <p className="completed-summary">{repair.summary}</p>

      {/* Duration, crew, cost — everything at a glance */}
      <div className="completed-stat-row">
        <div className="completed-stat">
          <CalendarClock size={15} />
          <div>
            <strong>
              {repair.actual_days.toFixed(1)}d
              <span className={onTime ? "on-time" : "late"}>
                {onTime ? " on time" : ` (${(repair.actual_days - repair.promised_days).toFixed(1)}d over)`}
              </span>
            </strong>
            <span>of {repair.promised_days.toFixed(0)}d promised</span>
          </div>
        </div>
        <div className="completed-stat">
          <Users size={15} />
          <div>
            <strong>{repair.crew_count}-person crew</strong>
            <span>{repair.contractor_name}</span>
          </div>
        </div>
        <div className="completed-stat">
          <Banknote size={15} />
          <div>
            <strong>{formatInr(repair.awarded_inr)}</strong>
            <span>
              {repair.savings_inr >= 0
                ? `${formatInr(repair.savings_inr)} under estimate`
                : `${formatInr(-repair.savings_inr)} over estimate`}
            </span>
          </div>
        </div>
        <div className="completed-stat">
          <Star size={15} />
          <div>
            <strong>{repair.contractor_rating.toFixed(1)} / 5</strong>
            <span>{repair.contractor_specialty}</span>
          </div>
        </div>
      </div>

      {/* What charges are involved — concise, not the full itemized BOQ */}
      <div className="completed-charges">
        <span className="completed-block-label">
          <ClipboardCheck size={13} /> Charges
        </span>
        <ul>
          {repair.charges.map((charge) => (
            <li key={charge.label} className={charge.label === "Awarded contract value" ? "is-total" : undefined}>
              <span>
                {charge.label}
                {charge.note && <em>{charge.note}</em>}
              </span>
              <strong>{formatInr(charge.amount_inr)}</strong>
            </li>
          ))}
        </ul>
      </div>

      {/* The contractor's own handover notice */}
      <div className="completed-notice">
        <span className="completed-block-label">
          <HardHat size={13} /> Contractor handover notice
          <code>{repair.note.reference}</code>
        </span>
        <p>{repair.note.statement}</p>
        <div className="completed-notice-meta">
          <span>
            <CheckCircle2 size={12} /> {repair.note.defect_liability_months}-month defect liability
          </span>
          <span>Reopened to traffic after {repair.note.traffic_reopened_after_hours}h</span>
        </div>
        <div className="completed-notice-sign">
          <span>{repair.note.signed_by}</span>
          <span>{formatClock(repair.note_issued_at)}</span>
        </div>
      </div>
    </article>
  );
}
