"use client";

import { useCallback, useEffect, useState } from "react";
import { Check } from "lucide-react";
import { getPipelineStats } from "@/lib/api";
import type { PipelineStats } from "@/lib/types";

interface StepNode {
  label: string;
  count: number | null;
  state: "done" | "active" | "pending";
}

/**
 * End-to-end flow across the whole app, driven by real pipeline counters —
 * detection, then a filed municipal grievance, then a verified repair. Each
 * node is "done" only when something has actually reached it.
 */
export function StepperPipeline() {
  const [stats, setStats] = useState<PipelineStats | null>(null);

  const load = useCallback(async () => {
    try {
      setStats(await getPipelineStats());
    } catch {
      // The workspace surfaces API problems; the header just stays neutral.
    }
  }, []);

  useEffect(() => {
    // The first poll is queued rather than run inline, so state only ever
    // changes from a callback the external system drives — never from the
    // effect body itself (React compiler lint), and a mount renders once.
    const first = setTimeout(load, 0);
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void load();
    }, 6000);
    window.addEventListener("crackmap:refresh", load);
    return () => {
      clearTimeout(first);
      clearInterval(id);
      window.removeEventListener("crackmap:refresh", load);
    };
  }, [load]);

  const filed = stats ? stats.total_cases - (stats.stage_counts.DRAFT ?? 0) : 0;
  const repaired = stats
    ? (stats.stage_counts.VERIFIED ?? 0) + (stats.stage_counts.CLOSED ?? 0)
    : 0;

  const nodes: StepNode[] = [
    {
      label: "Road imagery inspected",
      count: stats?.total_findings ?? null,
      state: (stats?.total_findings ?? 0) > 0 ? "done" : "active",
    },
    {
      label: "Grievances filed with authority",
      count: stats ? filed : null,
      state: filed > 0 ? "done" : (stats?.total_findings ?? 0) > 0 ? "active" : "pending",
    },
    {
      label: "Repairs verified & certified",
      count: stats ? repaired : null,
      state: repaired > 0 ? "done" : filed > 0 ? "active" : "pending",
    },
  ];

  const doneCount = nodes.filter((n) => n.state === "done").length;
  const nodeCount = nodes.length;
  const edgePct = 50 / nodeCount;
  const trackWidthPct = 100 - 100 / nodeCount;
  const filledSegments = Math.max(0, doneCount - 1);
  const fillPct = nodeCount > 1 ? (filledSegments / (nodeCount - 1)) * trackWidthPct : 0;

  return (
    <div className="stepper-pipeline">
      <div className="stepper-track" style={{ left: `${edgePct}%`, width: `${trackWidthPct}%` }} />
      <div className="stepper-track-fill" style={{ left: `${edgePct}%`, width: `${fillPct}%` }} />
      {nodes.map((node, i) => (
        <div className="stepper-node" key={node.label}>
          <div
            className={`node-circle${node.state === "done" ? " done" : ""}${
              node.state === "active" ? " active" : ""
            }`}
          >
            {node.state === "done" ? <Check size={14} /> : i + 1}
          </div>
          <div className="node-label">
            {node.label}
            {node.count !== null && <strong> · {node.count}</strong>}
          </div>
        </div>
      ))}
    </div>
  );
}
