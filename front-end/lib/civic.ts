import type { CaseStatus, CaseView, SlaState } from "./types";

/** Visual identity for each pipeline stage, shared by the rail, cards and map. */
export const STAGE_META: Record<
  CaseStatus,
  { short: string; label: string; color: string; owner: string }
> = {
  DRAFT: { short: "Triage", label: "Intake & Triage", color: "#64748b", owner: "Field inspector" },
  SUBMITTED: { short: "Filed", label: "Filed to Portal", color: "#3b82f6", owner: "Filing agent" },
  ACKNOWLEDGED: { short: "Acknowledged", label: "Acknowledged by Authority", color: "#6366f1", owner: "Municipal portal" },
  TENDERED: { short: "Tender", label: "Tender & Bidding", color: "#f59e0b", owner: "Municipal engineer" },
  WORK_ORDERED: { short: "Work Order", label: "Work Order Issued", color: "#f97316", owner: "Municipal engineer" },
  IN_REPAIR: { short: "Repairing", label: "Repair In Progress", color: "#eab308", owner: "Contractor crew" },
  REPAIRED: { short: "Re-Inspect", label: "Awaiting Re-Inspection", color: "#06b6d4", owner: "Contractor crew" },
  VERIFIED: { short: "Verified", label: "Re-Inspection Passed", color: "#16a34a", owner: "CrackMap AI" },
  CLOSED: { short: "Closed", label: "Case Closed", color: "#15803d", owner: "Municipal engineer" },
};

export const STAGE_ORDER: CaseStatus[] = [
  "DRAFT",
  "SUBMITTED",
  "ACKNOWLEDGED",
  "TENDERED",
  "WORK_ORDERED",
  "IN_REPAIR",
  "REPAIRED",
  "VERIFIED",
  "CLOSED",
];

export const PRIORITY_COLOR: Record<string, string> = {
  P1: "#ef4444",
  P2: "#f59e0b",
  P3: "#3b82f6",
  P4: "#64748b",
};

export const SLA_COLOR: Record<SlaState, string> = {
  NOT_STARTED: "#94a3b8",
  ON_TRACK: "#16a34a",
  AT_RISK: "#f59e0b",
  BREACHED: "#ef4444",
  MET: "#16a34a",
};

export const SLA_LABEL: Record<SlaState, string> = {
  NOT_STARTED: "Not filed",
  ON_TRACK: "On track",
  AT_RISK: "At risk",
  BREACHED: "Response window missed",
  MET: "Responded in time",
};

/**
 * What moves this case forward next.
 *
 * `kind: "waiting"` stages are the ones the backend advances on its own clock —
 * the UI shows a live status there instead of a button, which is the whole
 * point: no Next button for something a municipality does by itself.
 */
export type NextStep =
  | { kind: "action"; action: "submit" | "tender" | "award" | "verify" | "close"; label: string; hint: string }
  | { kind: "waiting"; label: string; hint: string }
  | { kind: "done"; label: string; hint: string };

export function nextStep(caseView: CaseView): NextStep {
  switch (caseView.status) {
    case "DRAFT":
      return {
        kind: "action",
        action: "submit",
        label: "File with the municipal portal",
        hint: "Routes by coordinate to the authority that owns this road and mints a grievance number.",
      };
    case "SUBMITTED":
      return {
        kind: "waiting",
        label: "Awaiting portal acknowledgement",
        hint: "The authority's intake cell is registering the grievance and assigning an officer.",
      };
    case "ACKNOWLEDGED":
      return {
        kind: "action",
        action: "tender",
        label: "Float tender to the contractor panel",
        hint: "Invites every empanelled contractor to quote against the priced bill of quantities.",
      };
    case "TENDERED":
      return {
        kind: "action",
        action: "award",
        label: "Award the work order",
        hint: "Pick a bid on price, promised duration and contractor rating.",
      };
    case "WORK_ORDERED":
      return {
        kind: "waiting",
        label: "Crew mobilising to site",
        hint: "The awarded contractor is moving plant and crew to the location.",
      };
    case "IN_REPAIR":
      return {
        kind: "waiting",
        label: "Repair underway",
        hint: "Hot-mix patching, compaction and edge sealing in progress.",
      };
    case "REPAIRED":
      return {
        kind: "action",
        action: "verify",
        label: "Run AI re-inspection",
        hint: "Upload an after-photo; the same detector scores the repair and can send it back as rework.",
      };
    case "VERIFIED":
      return {
        kind: "action",
        action: "close",
        label: "Close case & issue certificate",
        hint: "Releases the completion certificate for the grievance record.",
      };
    case "CLOSED":
      return {
        kind: "done",
        label: "Case closed",
        hint: "Dossier and completion certificate are available below.",
      };
  }
}

/** Indian-format currency, which is what the BOQ rates are quoted in. */
export function formatInr(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}

export function formatCompactInr(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}k`;
  return `₹${Math.round(value)}`;
}

export function formatClock(timestamp: number | null | undefined): string {
  if (!timestamp) return "—";
  return new Date(timestamp * 1000).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "12s ago" / "4m ago" — for live feeds where absolute time adds nothing. */
export function formatAgo(timestamp: number | null | undefined, now: number): string {
  if (!timestamp) return "—";
  const seconds = Math.max(0, Math.round(now - timestamp));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/**
 * Municipal hours remaining, phrased the way a grievance tracker would.
 *
 * The window is a response deadline: it stops when the work order is issued,
 * not when the asphalt cures. Mirrors civic.sla_status on the backend.
 */
export function formatSlaRemaining(caseView: CaseView, now: number): string {
  if (caseView.sla_due_at === null || caseView.sla_hours === null) {
    // The window only starts once the authority acknowledges, so a filed case
    // is waiting on them, not on us.
    return caseView.submitted_at !== null ? "Awaiting acknowledgement" : "Not filed";
  }
  const respondedAt = caseView.awarded?.awarded_at ?? null;
  const reference = respondedAt ?? now;
  const simHours = ((caseView.sla_due_at - reference) / caseView.seconds_per_sim_day) * 24;
  const magnitude = Math.abs(simHours);
  const rendered = magnitude >= 48 ? `${(magnitude / 24).toFixed(1)}d` : `${magnitude.toFixed(1)}h`;
  if (respondedAt !== null) {
    return simHours >= 0 ? `Responded with ${rendered} to spare` : `Responded ${rendered} late`;
  }
  return simHours >= 0 ? `${rendered} left of ${caseView.sla_hours}h` : `${rendered} overdue`;
}

/**
 * Repair progress interpolated on the client clock.
 *
 * The server sends a snapshot every poll; this keeps the bar moving in between
 * using the same mobilisation lag and promised duration the server used.
 */
const MOBILISATION_LAG_DAYS = 1.0;

export function liveRepairProgress(caseView: CaseView, now: number): number {
  const awardedAt = caseView.awarded?.awarded_at;
  const promisedDays = caseView.awarded?.promised_days;
  if (!awardedAt || !promisedDays) return caseView.repair_progress_pct;
  if (caseView.repaired_at) return 100;

  const simDays = Math.max(0, (now - awardedAt) / caseView.seconds_per_sim_day);
  const workDays = Math.max(0, simDays - MOBILISATION_LAG_DAYS);
  const pct = Math.min(100, (workDays / Math.max(0.25, promisedDays)) * 100);
  // Never rewind below what the server already reported.
  return Math.max(caseView.repair_progress_pct, Number(pct.toFixed(1)));
}

export function simDaysSince(timestamp: number | null | undefined, now: number, secondsPerSimDay: number): number {
  if (!timestamp) return 0;
  return Math.max(0, (now - timestamp) / secondsPerSimDay);
}
