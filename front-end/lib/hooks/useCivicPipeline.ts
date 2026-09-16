"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getCases, getInspections, getPipelineStats } from "@/lib/api";
import type { CaseView, Inspection, PipelineStats } from "@/lib/types";

export interface CivicPipelineState {
  cases: CaseView[];
  findings: Inspection[];
  stats: PipelineStats | null;
  lastUpdated: number | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Live view of the civic pipeline.
 *
 * Polls while the tab is visible, because several stages (portal
 * acknowledgement, crew mobilisation, repair completion) advance on the
 * backend's simulated clock with nobody clicking anything — without polling the
 * board would silently go stale.
 */
export function useCivicPipeline(isActive: boolean, intervalMs = 2500): CivicPipelineState {
  const [cases, setCases] = useState<CaseView[]>([]);
  const [findings, setFindings] = useState<Inspection[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Guards against overlapping polls on a slow backend, and against setting
  // state after unmount.
  const inFlight = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const load = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setIsLoading(true);
    try {
      const [nextCases, nextFindings, nextStats] = await Promise.all([
        getCases(),
        getInspections(),
        getPipelineStats(),
      ]);
      if (!mounted.current) return;
      setCases(nextCases);
      setFindings(nextFindings);
      setStats(nextStats);
      setLastUpdated(Date.now() / 1000);
      setError(null);
    } catch (err) {
      if (!mounted.current) return;
      setError(err instanceof Error ? err.message : "Could not reach the pipeline API");
    } finally {
      inFlight.current = false;
      if (mounted.current) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isActive) return;
    // The first poll is queued rather than run inline, so state only ever
    // changes from a callback the external system drives — never from the
    // effect body itself (React compiler lint), and a mount renders once.
    const first = setTimeout(load, 0);
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void load();
    }, intervalMs);
    return () => {
      clearTimeout(first);
      clearInterval(id);
    };
  }, [isActive, intervalMs, load]);

  useEffect(() => {
    const onRefresh = () => void load();
    window.addEventListener("crackmap:refresh", onRefresh);
    return () => window.removeEventListener("crackmap:refresh", onRefresh);
  }, [load]);

  return { cases, findings, stats, lastUpdated, isLoading, error, refresh: () => void load() };
}
