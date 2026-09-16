"use client";

import { useMemo, useState } from "react";
import { FolderPlus, Inbox, Loader2, MapPin } from "lucide-react";
import { createCase } from "@/lib/api";
import { PRIORITY_COLOR, formatAgo, formatCompactInr } from "@/lib/civic";
import { useNow } from "@/lib/hooks/useNow";
import type { Inspection } from "@/lib/types";

interface IntakeQueueProps {
  findings: Inspection[];
  onCaseOpened: (caseId: number) => void;
}

/** Rough engineer's estimate so the operator sees the cost before filing. */
const INR_PER_M2 = 2381; // BOQ subtotal + overheads + GST, per m², from civic.build_boq

export function IntakeQueue({ findings, onCaseOpened }: IntakeQueueProps) {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const now = useNow(5000);

  const unassigned = useMemo(() => findings.filter((f) => f.case_id === null), [findings]);

  const selectedFindings = unassigned.filter((f) => selected.has(f.id));
  const selectedPotholes = selectedFindings.reduce((sum, f) => sum + f.total_defects, 0);
  const selectedArea = selectedFindings.reduce((sum, f) => sum + (f.patch_area_m2 ?? 0), 0);

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => (prev.size === unassigned.length ? new Set() : new Set(unassigned.map((f) => f.id))));
  }

  async function handleOpenCase() {
    if (selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      const created = await createCase(Array.from(selected));
      setSelected(new Set());
      window.dispatchEvent(new CustomEvent("crackmap:refresh"));
      onCaseOpened(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open a case");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="civic-panel">
      <header className="civic-panel-head">
        <div>
          <h4>
            <Inbox size={17} />
            Intake queue
            <span className="civic-count-chip">{unassigned.length}</span>
          </h4>
          <p>
            Findings logged from the Inspection Studio, triaged and priced, waiting to be bundled into
            a municipal grievance.
          </p>
        </div>
        {unassigned.length > 0 && (
          <div className="civic-intake-actions">
            <button type="button" className="ghost-btn" onClick={toggleAll}>
              {selected.size === unassigned.length ? "Clear selection" : "Select all"}
            </button>
            <button
              type="button"
              className="primary-pill-btn"
              disabled={selected.size === 0 || busy}
              onClick={handleOpenCase}
            >
              {busy ? <Loader2 size={15} className="spin-animation" /> : <FolderPlus size={15} />}
              Open case from {selected.size} finding{selected.size === 1 ? "" : "s"}
            </button>
          </div>
        )}
      </header>

      {selected.size > 0 && (
        <div className="civic-selection-summary">
          <span>
            <strong>{selectedPotholes}</strong> potholes
          </span>
          <span>
            <strong>{selectedArea.toFixed(2)} m²</strong> patch area
          </span>
          <span>
            ≈ <strong>{formatCompactInr(selectedArea * INR_PER_M2)}</strong> engineer&rsquo;s estimate
          </span>
        </div>
      )}

      {error && <p className="batch-status error">{error}</p>}

      {unassigned.length === 0 ? (
        <div className="civic-empty">
          <MapPin size={22} />
          <p>
            <strong>Nothing waiting.</strong> Run a detection in the <em>Inspection Studio</em> tab, capture
            the location, then log it — it lands here for triage.
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table className="defect-table civic-table">
            <thead>
              <tr>
                <th aria-label="select" />
                <th>Finding</th>
                <th>Location</th>
                <th>Road class</th>
                <th>Potholes</th>
                <th>Severity</th>
                <th>Patch area</th>
                <th>Priority</th>
                <th>Logged</th>
              </tr>
            </thead>
            <tbody>
              {unassigned.map((finding) => (
                <tr
                  key={finding.id}
                  className={selected.has(finding.id) ? "is-selected" : undefined}
                  onClick={() => toggle(finding.id)}
                >
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(finding.id)}
                      onChange={() => toggle(finding.id)}
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Select finding ${finding.id}`}
                    />
                  </td>
                  <td>
                    <strong>#{finding.id}</strong>
                    <span className="civic-subtle">{finding.filename}</span>
                  </td>
                  <td>
                    <strong>{finding.road_name}</strong>
                    <span className="civic-subtle">
                      {finding.lat !== null && finding.lon !== null
                        ? `${finding.lat.toFixed(5)}, ${finding.lon.toFixed(5)}`
                        : "no coordinate captured"}
                    </span>
                  </td>
                  <td>{finding.road_class ?? "Local"}</td>
                  <td>{finding.total_defects}</td>
                  <td>{finding.severity_score}/5</td>
                  <td>{finding.patch_area_m2 ?? 0} m²</td>
                  <td>
                    <span
                      className="civic-pill"
                      style={{
                        color: PRIORITY_COLOR[finding.priority ?? "P4"],
                        borderColor: PRIORITY_COLOR[finding.priority ?? "P4"],
                      }}
                      title={finding.priority_label ?? undefined}
                    >
                      {finding.priority ?? "—"}
                    </span>
                  </td>
                  <td>{formatAgo(finding.created_at, now)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
