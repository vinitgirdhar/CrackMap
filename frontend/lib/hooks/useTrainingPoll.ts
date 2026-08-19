"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getTrainingStatus, startTraining } from "@/lib/api";
import type { StartTrainingParams, TrainingJobStatus } from "@/lib/types";

const POLL_INTERVAL_MS = 800;

interface UseTrainingPollResult {
  status: TrainingJobStatus | null;
  isTraining: boolean;
  startError: string | null;
  start: (params: StartTrainingParams) => Promise<void>;
}

/**
 * Ported from app.js triggerTrainingRun's setInterval poll loop.
 * Unlike the original, this clears the interval on unmount too (the
 * original leaks it if the user navigates away mid-run).
 */
export function useTrainingPoll(onCompleted?: () => void): UseTrainingPollResult {
  const [status, setStatus] = useState<TrainingJobStatus | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onCompletedRef = useRef(onCompleted);

  useEffect(() => {
    onCompletedRef.current = onCompleted;
  }, [onCompleted]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const start = useCallback(
    async (params: StartTrainingParams) => {
      setStartError(null);
      try {
        const res = await startTraining(params);
        if (!res.success) {
          setStartError(res.message || "Could not start training");
          return;
        }
      } catch (err) {
        setStartError(err instanceof Error ? err.message : "Failed to start training");
        return;
      }

      stopPolling();
      intervalRef.current = setInterval(async () => {
        try {
          const jobStatus = await getTrainingStatus();
          setStatus(jobStatus);
          if (jobStatus.status === "completed" || jobStatus.status === "failed") {
            stopPolling();
            if (jobStatus.status === "completed") {
              onCompletedRef.current?.();
            }
          }
        } catch {
          stopPolling();
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  return {
    status,
    isTraining: status?.status === "training",
    startError,
    start,
  };
}
