const EQUALIZER_COLS = 20;
const EQUALIZER_ROWS = 4;
const EQUALIZER_TOTAL_SLOTS = EQUALIZER_COLS * EQUALIZER_ROWS;

export type EqualizerDotState = "empty" | "red" | "teal";

/** Ported from app.js renderDynamicEqualizer: pothole/crack dot-slot math. */
export function computeEqualizerDots(
  potholes: number,
  cracks: number
): EqualizerDotState[] {
  const potholeSlots = Math.min(EQUALIZER_TOTAL_SLOTS, potholes * 3);
  const crackSlots = Math.min(EQUALIZER_TOTAL_SLOTS - potholeSlots, cracks * 2);

  return Array.from({ length: EQUALIZER_TOTAL_SLOTS }, (_, i) => {
    if (i < potholeSlots) return "red";
    if (i < potholeSlots + crackSlots) return "teal";
    return "empty";
  });
}

export interface MicroBar {
  code: string;
  label: string;
  value: number;
  pct: number;
}

const MICRO_BAR_CLASSES: { code: string; label: string }[] = [
  { code: "D00", label: "Long." },
  { code: "D10", label: "Trans." },
  { code: "D20", label: "Allig." },
  { code: "D40", label: "Pothole" },
];

/** Ported from app.js renderMicroBars: per-class bar height math. */
export function computeMicroBars(
  classDistribution: Record<string, number>
): MicroBar[] {
  const maxVal = Math.max(
    1,
    ...MICRO_BAR_CLASSES.map((k) => classDistribution[k.code] ?? 0)
  );

  return MICRO_BAR_CLASSES.map((k) => {
    const value = classDistribution[k.code] ?? 0;
    const pct = Math.max(15, Math.round((value / maxVal) * 90));
    return { code: k.code, label: k.label, value, pct };
  });
}

export type SeverityLevel = "low" | "medium" | "high";

/** Ported from app.js fetchDashboardSummary's severity-description thresholds. */
export function severityLevel(avgSeverity: number): SeverityLevel {
  if (avgSeverity >= 2.5) return "high";
  if (avgSeverity >= 1.5) return "medium";
  return "low";
}
