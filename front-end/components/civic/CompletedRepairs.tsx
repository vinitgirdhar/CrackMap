"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { getCompletedRepairs } from "@/lib/api";
import type { CompletedRepair } from "@/lib/types";
import { CompletedRepairCard } from "./CompletedRepairCard";

interface CompletedRepairsProps {
  isActive: boolean;
}

/**
 * The finished product of the pipeline: every case a re-inspection has
 * passed, shown as a before/after record — not a stat, an artefact. Sits
 * below the case board and renders nothing until the first repair is
 * verified, so an empty demo does not show a placeholder gallery.
 *
 * Polled more loosely than the board (these payloads carry two full images
 * each) and refreshed on demand whenever any case action fires
 * `crackmap:refresh`, which covers the moment a repair is actually verified.
 */
export function CompletedRepairs({ isActive }: CompletedRepairsProps) {
  const [repairs, setRepairs] = useState<CompletedRepair[]>([]);
  const [hasLoaded, setHasLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      setRepairs(await getCompletedRepairs());
    } catch {
      // The board already surfaces connection problems elsewhere; leave
      // whatever was last shown here rather than blanking it on a hiccup.
    } finally {
      setHasLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!isActive) return;
    // Queued rather than run inline so the effect body itself never calls
    // setState (React compiler lint) — the first poll fires on the next tick.
    const first = setTimeout(load, 0);
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void load();
    }, 10000);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [isActive, load]);

  useEffect(() => {
    window.addEventListener("crackmap:refresh", load);
    return () => window.removeEventListener("crackmap:refresh", load);
  }, [load]);

  if (!hasLoaded || repairs.length === 0) return null;

  return (
    <section className="civic-panel completed-panel">
      <header className="civic-panel-head">
        <div>
          <h4>
            <CheckCircle2 size={17} />
            Completed repairs
            <span className="civic-count-chip">{repairs.length}</span>
          </h4>
          <p>
            Before/after evidence, cost, duration and the contractor&rsquo;s own handover notice for every
            repair an AI re-inspection has verified.
          </p>
        </div>
      </header>

      <div className="completed-grid">
        {repairs.map((repair) => (
          <CompletedRepairCard key={repair.case_id} repair={repair} />
        ))}
      </div>
    </section>
  );
}
