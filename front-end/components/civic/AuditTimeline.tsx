"use client";

import { STAGE_META, formatAgo, formatClock } from "@/lib/civic";
import type { CaseStatus, PipelineEvent } from "@/lib/types";

interface AuditTimelineProps {
  events: PipelineEvent[];
  now: number;
  /** Newest first, for the global feed; oldest first reads better per case. */
  newestFirst?: boolean;
  compact?: boolean;
}

/**
 * The audit trail. Every stage transition — including the ones nobody clicked —
 * is a real persisted row, so this is the evidence log a municipality would
 * attach to the grievance, not a UI animation.
 */
export function AuditTimeline({ events, now, newestFirst = false, compact = false }: AuditTimelineProps) {
  const ordered = newestFirst ? [...events].reverse() : events;

  if (ordered.length === 0) {
    return <p className="civic-subtle">No pipeline activity recorded yet.</p>;
  }

  return (
    <ol className={`audit-timeline${compact ? " is-compact" : ""}`}>
      {ordered.map((event) => {
        const color = STAGE_META[event.stage as CaseStatus]?.color ?? "#94a3b8";
        return (
          <li key={event.id} style={{ "--stage-color": color } as React.CSSProperties}>
            <span className="audit-dot" aria-hidden />
            <div className="audit-body">
              <div className="audit-head">
                <span className="audit-title">{event.title}</span>
                <time className="audit-time" title={formatClock(event.created_at)}>
                  {formatAgo(event.created_at, now)}
                </time>
              </div>
              <span className="audit-actor">{event.actor}</span>
              {event.detail && !compact && <p className="audit-detail">{event.detail}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
