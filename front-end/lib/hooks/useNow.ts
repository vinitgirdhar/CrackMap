"use client";

import { useEffect, useState } from "react";

/**
 * A ticking clock, so SLA countdowns and repair progress bars move smoothly
 * between server polls instead of jumping once every few seconds.
 *
 * Returns unix seconds (matching the backend's timestamps), not milliseconds.
 */
export function useNow(intervalMs = 1000, enabled = true): number {
  const [now, setNow] = useState(() => Date.now() / 1000);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => setNow(Date.now() / 1000), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);

  return now;
}
