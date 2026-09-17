"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  Building2,
  Check,
  Circle,
  Clock,
  Copy,
  Loader2,
  MapPin,
  Plus,
  Radio,
  ShieldCheck,
} from "lucide-react";
import { getCitizenCase } from "@/lib/api";
import { formatClock } from "@/lib/civic";
import { useNow } from "@/lib/hooks/useNow";
import type { CitizenCaseView } from "@/lib/types";

interface CitizenTrackerProps {
  caseId: number;
  onReportAnother: () => void;
}

const PRIORITY_COLOR: Record<string, string> = {
  P1: "#ef4444",
  P2: "#f59e0b",
  P3: "#3b82f6",
  P4: "#64748b",
};

/**
 * A citizen's own view of one report: what stage it is at, in plain
 * language, and — once resolved — the before/after proof and a one-line
 * summary of what was fixed. No contractor identity, no cost figure appears
 * anywhere here: the API this polls filters both out server-side.
 */
export function CitizenTracker({ caseId, onReportAnother }: CitizenTrackerProps) {
  const [view, setView] = useState<CitizenCaseView | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);
  const now = useNow(1000);

  const load = useCallback(async () => {
    try {
      setView(await getCitizenCase(caseId));
      setNotFound(false);
    } catch {
      setNotFound(true);
    }
  }, [caseId]);

  useEffect(() => {
    // Queued rather than called inline so the effect body itself never calls
    // setState (React compiler lint) — the first poll fires on the next tick.
    const first = setTimeout(load, 0);
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void load();
    }, 4000);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [load]);

  function copyLink() {
    try {
      void navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API unavailable (e.g. insecure context) — link is still
      // visible in the address bar, so this is a nice-to-have only.
    }
  }

  if (notFound) {
    return (
      <div className="citizen-card citizen-notfound">
        <AlertCircle size={28} />
        <h2>We couldn&rsquo;t find that report</h2>
        <p>The link may be wrong, or the report may no longer exist.</p>
        <button type="button" className="citizen-submit-btn" onClick={onReportAnother}>
          <Plus size={16} /> Report a pothole
        </button>
      </div>
    );
  }

  if (!view) {
    return (
      <div className="citizen-card citizen-loading">
        <Loader2 size={26} className="spin-animation" />
        <p>Loading your report…</p>
      </div>
    );
  }

  return (
    <div className="citizen-card citizen-tracker">
      <div className="citizen-tracker-head">
        <div>
          <span className="citizen-tracking-label">Tracking ID</span>
          <div className="citizen-tracking-id">
            {view.tracking_id ?? "Registering…"}
            {view.tracking_id && (
              <button type="button" className="citizen-copy-btn" onClick={copyLink} title="Copy tracking link">
                {copied ? <Check size={14} /> : <Copy size={14} />}
              </button>
            )}
          </div>
        </div>
        {view.priority_label && (
          <span
            className="citizen-priority-pill"
            style={{ color: PRIORITY_COLOR[view.priority ?? ""] ?? "#64748b" }}
          >
            {view.priority_label}
          </span>
        )}
      </div>

      <div className="citizen-road-row">
        <MapPin size={15} />
        <div>
          <strong>{view.road_name}</strong>
          {view.address && <span>{view.address}</span>}
        </div>
      </div>

      {view.authority && (
        <div className="citizen-authority-row">
          <Building2 size={14} />
          {view.authority}
          {view.department ? ` · ${view.department}` : ""}
        </div>
      )}

      <p className="citizen-reported-at">
        <Clock size={12} /> Reported {formatClock(view.reported_at)}
      </p>

      {/* Status timeline — the "upper-level view": what stage the road is at,
          in plain language, never who is doing it or what it costs. */}
      <ol className="citizen-timeline">
        {view.stages.map((stage) => (
          <li
            key={stage.key}
            className={stage.completed ? "is-done" : stage.active ? "is-active" : "is-pending"}
          >
            <span className="citizen-timeline-dot" aria-hidden>
              {stage.completed ? (
                <Check size={12} />
              ) : stage.active ? (
                <Radio size={11} className="pulse-icon" />
              ) : (
                <Circle size={8} />
              )}
            </span>
            <div className="citizen-timeline-body">
              <div className="citizen-timeline-head">
                <strong>{stage.label}</strong>
                {stage.at && <time>{formatClock(stage.at)}</time>}
              </div>
              <span>{stage.description}</span>
            </div>
          </li>
        ))}
      </ol>

      {/* Resolved: the finished product for this one road, nothing about
          who did it or what it cost. */}
      {view.is_resolved && (
        <section className="citizen-resolved">
          <div className="citizen-resolved-head">
            <ShieldCheck size={18} />
            <strong>Repair verified</strong>
          </div>

          <div className="completed-evidence">
            <div className="completed-evidence-pane">
              <span className="completed-evidence-tag before">Before</span>
              {view.before_image ? (
                // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
                <img src={view.before_image} alt={`${view.road_name} before repair`} />
              ) : (
                <div className="completed-evidence-placeholder">No frame stored</div>
              )}
            </div>
            <div className="completed-evidence-pane">
              <span className="completed-evidence-tag after">After</span>
              {view.after_image ? (
                // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
                <img src={view.after_image} alt={`${view.road_name} after repair`} />
              ) : (
                <div className="completed-evidence-placeholder">No frame stored</div>
              )}
            </div>
          </div>

          {view.description && <p className="citizen-resolved-description">{view.description}</p>}

          {view.fix_summary && <p className="citizen-fix-summary">{view.fix_summary}</p>}
        </section>
      )}

      <button type="button" className="citizen-report-another" onClick={onReportAnother}>
        <Plus size={15} /> Report another pothole
      </button>

      <p className="citizen-live-note">
        <Radio size={11} className="pulse-icon" /> This page updates on its own — no need to refresh.
        {" "}Last checked just now, as of {formatClock(now)}.
      </p>
    </div>
  );
}
