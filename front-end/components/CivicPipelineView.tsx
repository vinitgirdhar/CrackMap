"use client";

import { useMemo, useState } from "react";
import { ClipboardList, Gauge, LayoutGrid, RefreshCw, ServerCrash, WifiOff } from "lucide-react";
import { useCivicPipeline } from "@/lib/hooks/useCivicPipeline";
import { useNow } from "@/lib/hooks/useNow";
import { STAGE_META, formatAgo } from "@/lib/civic";
import type { CaseStatus } from "@/lib/types";
import { GisView } from "./GisView";
import { CaseCard } from "./civic/CaseCard";
import { CaseDetail } from "./civic/CaseDetail";
import { CompletedRepairs } from "./civic/CompletedRepairs";
import { IntakeQueue } from "./civic/IntakeQueue";
import { KpiStrip } from "./civic/KpiStrip";
import { LiveFeed } from "./civic/LiveFeed";
import { StageRail } from "./civic/StageRail";

interface CivicPipelineViewProps {
  isActive: boolean;
}

export function CivicPipelineView({ isActive }: CivicPipelineViewProps) {
  const { cases, findings, stats, lastUpdated, isLoading, error, isStaleBackend, refresh } =
    useCivicPipeline(isActive);
  const [filter, setFilter] = useState<CaseStatus | "ALL">("ALL");
  const [openCaseId, setOpenCaseId] = useState<number | null>(null);
  const now = useNow(1000, isActive);

  const visibleCases = useMemo(
    () => (filter === "ALL" ? cases : cases.filter((c) => c.status === filter)),
    [cases, filter]
  );

  const focusPointId = useMemo(() => {
    if (openCaseId === null) return null;
    const opened = cases.find((c) => c.id === openCaseId);
    return opened?.findings.find((f) => f.lat !== null)?.id ?? null;
  }, [openCaseId, cases]);

  const simSpeed = stats ? Math.round(86400 / stats.seconds_per_sim_day) : null;

  return (
    <div className="civic-workspace">
      <header className="workspace-header civic-workspace-header">
        <div>
          <h3 className="section-headline">
            <ClipboardList size={22} />
            Civic Repair Pipeline
          </h3>
          <p className="section-subtext">
            Findings become municipal grievances, grievances become priced work orders, work orders
            become verified repairs — each stage evidenced, costed and exportable.
          </p>
        </div>
        <div className="civic-header-meta">
          {simSpeed && (
            <span className="sim-clock-badge" title="Municipal days are compressed so a full repair cycle is watchable">
              <Gauge size={13} /> simulated clock ×{simSpeed.toLocaleString()}
            </span>
          )}
          <button
            type="button"
            className={`ghost-btn${isLoading ? " is-busy" : ""}`}
            onClick={refresh}
            aria-label="Refresh pipeline"
          >
            <RefreshCw size={14} className={isLoading ? "spin-animation" : ""} />
            {lastUpdated ? formatAgo(lastUpdated, now) : "loading"}
          </button>
        </div>
      </header>

      {isStaleBackend ? (
        <section className="stale-backend-notice">
          <ServerCrash size={22} />
          <div>
            <strong>The backend is running an older build</strong>
            <p>
              It answered, but without the <code>/api/civic/*</code> routes this workspace needs, so
              there is nothing to show. Restart it and this page will fill in on its next poll.
            </p>
            <pre>python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload</pre>
            <p className="civic-footnote">
              If the backend is not on port 8000, point <code>BACKEND_URL</code> in{" "}
              <code>front-end/.env.local</code> at wherever it is listening.
            </p>
          </div>
        </section>
      ) : (
        error && (
          <p className="batch-status error civic-connection-error">
            <WifiOff size={14} /> {error}
          </p>
        )
      )}

      <KpiStrip stats={stats} />

      <StageRail stats={stats} activeFilter={filter} onFilterChange={setFilter} />

      <div className="civic-split">
        <GisView isActive={isActive} focusPointId={focusPointId} onSelectCase={setOpenCaseId} />
        <LiveFeed isActive={isActive} />
      </div>

      <IntakeQueue findings={findings} onCaseOpened={setOpenCaseId} />

      <section className="civic-panel">
        <header className="civic-panel-head">
          <div>
            <h4>
              <LayoutGrid size={17} />
              Case board
              <span className="civic-count-chip">{visibleCases.length}</span>
            </h4>
            <p>
              {filter === "ALL"
                ? "Every municipal grievance CrackMap has raised. Open one to file it, tender it, award it or verify the repair."
                : `Filtered to ${STAGE_META[filter].label}. Click the stage again to clear.`}
            </p>
          </div>
        </header>

        {visibleCases.length === 0 ? (
          <div className="civic-empty">
            <ClipboardList size={22} />
            <p>
              {cases.length === 0 ? (
                <>
                  <strong>No cases yet.</strong> Select findings in the intake queue above and open the
                  first grievance.
                </>
              ) : (
                <>
                  <strong>Nothing at this stage.</strong> Clear the filter to see all {cases.length} case(s).
                </>
              )}
            </p>
          </div>
        ) : (
          <div className="case-board">
            {visibleCases.map((caseView) => (
              <CaseCard
                key={caseView.id}
                caseView={caseView}
                now={now}
                isSelected={openCaseId === caseView.id}
                onOpen={setOpenCaseId}
              />
            ))}
          </div>
        )}
      </section>

      <CompletedRepairs isActive={isActive} />

      {openCaseId !== null && (
        <CaseDetail caseId={openCaseId} onClose={() => setOpenCaseId(null)} />
      )}
    </div>
  );
}
