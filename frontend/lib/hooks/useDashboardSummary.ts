"use client";

import { useCallback, useEffect, useState } from "react";
import { getDashboardSummary } from "@/lib/api";
import type { DashboardSummary } from "@/lib/types";

interface UseDashboardSummaryResult {
  data: DashboardSummary | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refetch: () => void;
}

export function useDashboardSummary(): UseDashboardSummaryResult {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getDashboardSummary()
      .then((summary) => {
        if (!cancelled) {
          setData(summary);
          setError(null);
          setLastUpdated(new Date());
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard summary");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshToken]);

  const refetch = useCallback(() => {
    setLoading(true);
    setRefreshToken((t) => t + 1);
  }, []);

  return { data, loading, error, lastUpdated, refetch };
}
