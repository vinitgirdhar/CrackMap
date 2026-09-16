import { describe, expect, it } from "vitest";
import {
  formatAgo,
  formatCompactInr,
  formatInr,
  formatSlaRemaining,
  liveRepairProgress,
  nextStep,
  STAGE_META,
  STAGE_ORDER,
} from "./civic";
import type { CaseStatus, CaseView } from "./types";

function makeCase(overrides: Partial<CaseView> = {}): CaseView {
  return {
    id: 1,
    status: "DRAFT",
    stage_index: 0,
    stage_label: "Intake & Triage",
    created_at: 1000,
    total_potholes: 3,
    avg_severity: 3.5,
    severity_label: "Moderate",
    severity_hex: "#f59e0b",
    priority: "P2",
    priority_label: "High",
    priority_score: 60,
    patch_area_m2: 1.5,
    estimate_inr: 5000,
    boq: null,
    portal: null,
    tracking_id: null,
    routing_note: null,
    officer: null,
    submitted_at: null,
    acknowledged_at: null,
    sla_hours: null,
    sla_due_at: null,
    sla_state: "NOT_STARTED",
    hours_remaining: null,
    breached: false,
    tendered_at: null,
    bids: [],
    awarded: null,
    repair_progress_pct: 0,
    repair_sim_days: 0,
    repaired_at: null,
    verification: null,
    verified_at: null,
    closed_at: null,
    seconds_per_sim_day: 12,
    findings: [],
    events: [],
    ...overrides,
  };
}

describe("stage metadata", () => {
  it("covers every stage in the pipeline order", () => {
    expect(STAGE_ORDER).toHaveLength(9);
    for (const stage of STAGE_ORDER) {
      expect(STAGE_META[stage]).toBeDefined();
      expect(STAGE_META[stage].color).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });
});

describe("nextStep", () => {
  it("offers an explicit action only where a human actually decides", () => {
    const actions: Record<string, string> = {};
    for (const status of STAGE_ORDER) {
      actions[status] = nextStep(makeCase({ status })).kind;
    }
    expect(actions).toEqual({
      DRAFT: "action",
      SUBMITTED: "waiting",
      ACKNOWLEDGED: "action",
      TENDERED: "action",
      WORK_ORDERED: "waiting",
      IN_REPAIR: "waiting",
      REPAIRED: "action",
      VERIFIED: "action",
      CLOSED: "done",
    });
  });

  it("names the action so a button never reads 'next'", () => {
    const step = nextStep(makeCase({ status: "ACKNOWLEDGED" }));
    expect(step.kind).toBe("action");
    expect(step.label.toLowerCase()).not.toContain("next");
    expect(step.hint.length).toBeGreaterThan(20);
  });
});

describe("currency formatting", () => {
  it("uses the Indian grouping the BOQ rates are quoted in", () => {
    expect(formatInr(1250000)).toBe("₹12,50,000");
    expect(formatInr(0)).toBe("₹0");
    expect(formatInr(null)).toBe("—");
  });

  it("compacts large values into lakh and crore", () => {
    expect(formatCompactInr(4500)).toBe("₹4.5k");
    expect(formatCompactInr(250000)).toBe("₹2.50 L");
    expect(formatCompactInr(35000000)).toBe("₹3.50 Cr");
    expect(formatCompactInr(600)).toBe("₹600");
    expect(formatCompactInr(undefined)).toBe("—");
  });
});

describe("formatAgo", () => {
  it("renders the coarsest useful unit", () => {
    expect(formatAgo(1000, 1005)).toBe("5s ago");
    expect(formatAgo(1000, 1000 + 125)).toBe("2m ago");
    expect(formatAgo(1000, 1000 + 7200)).toBe("2h ago");
    expect(formatAgo(1000, 1000 + 172800)).toBe("2d ago");
    expect(formatAgo(null, 1000)).toBe("—");
    // Clock skew must not produce negative ages.
    expect(formatAgo(2000, 1000)).toBe("0s ago");
  });
});

describe("formatSlaRemaining", () => {
  it("counts down in simulated municipal hours", () => {
    // 12s per simulated day, due 6s out -> 12 simulated hours left.
    const caseView = makeCase({ sla_hours: 24, sla_due_at: 1006, seconds_per_sim_day: 12 });
    expect(formatSlaRemaining(caseView, 1000)).toBe("12.0h left of 24h");
  });

  it("reports overdue cases as overdue", () => {
    const caseView = makeCase({ sla_hours: 24, sla_due_at: 1000, seconds_per_sim_day: 12 });
    expect(formatSlaRemaining(caseView, 1006)).toBe("12.0h overdue");
  });

  it("stops the clock when the work order is issued, not when the case closes", () => {
    const awarded = {
      contractor_id: 1,
      contractor_name: "SafeStreet Civil Works",
      specialty: "Emergency 24h repair",
      rating: 4.7,
      crew_count: 4,
      awarded_inr: 11800,
      promised_days: 2,
      variance_pct: -5.6,
      awarded_at: 1006,
    };
    const met = makeCase({ sla_hours: 72, sla_due_at: 1012, awarded, seconds_per_sim_day: 12 });
    expect(formatSlaRemaining(met, 999999)).toBe("Responded with 12.0h to spare");

    const late = makeCase({
      sla_hours: 72,
      sla_due_at: 1000,
      awarded: { ...awarded, awarded_at: 1024 },
      seconds_per_sim_day: 12,
    });
    expect(formatSlaRemaining(late, 999999)).toBe("Responded 2.0d late");

    // A long repair after a prompt response must not retroactively breach it.
    const closedLate = makeCase({
      sla_hours: 72,
      sla_due_at: 1012,
      awarded,
      closed_at: 99999,
      seconds_per_sim_day: 12,
    });
    expect(formatSlaRemaining(closedLate, 999999)).toBe("Responded with 12.0h to spare");
  });

  it("distinguishes an unfiled case from one waiting on the authority", () => {
    expect(formatSlaRemaining(makeCase(), 1000)).toBe("Not filed");
    expect(formatSlaRemaining(makeCase({ status: "SUBMITTED", submitted_at: 990 }), 1000)).toBe(
      "Awaiting acknowledgement"
    );
  });
});

describe("liveRepairProgress", () => {
  const awarded = {
    contractor_id: 1,
    contractor_name: "SafeStreet Civil Works",
    specialty: "Emergency 24h repair",
    rating: 4.7,
    crew_count: 4,
    awarded_inr: 11800,
    promised_days: 2,
    variance_pct: -5.6,
    awarded_at: 1000,
  };

  it("stays at zero through the mobilisation lag", () => {
    const caseView = makeCase({ status: "WORK_ORDERED", awarded });
    expect(liveRepairProgress(caseView, 1000)).toBe(0);
    expect(liveRepairProgress(caseView, 1011)).toBe(0);
  });

  it("interpolates between server polls", () => {
    const caseView = makeCase({ status: "IN_REPAIR", awarded, repair_progress_pct: 10 });
    // 1 sim day mobilisation + 1 of 2 work days = 50%.
    expect(liveRepairProgress(caseView, 1000 + 24)).toBe(50);
    expect(liveRepairProgress(caseView, 1000 + 40)).toBe(100);
  });

  it("never rewinds below the server snapshot", () => {
    const caseView = makeCase({ status: "IN_REPAIR", awarded, repair_progress_pct: 80 });
    expect(liveRepairProgress(caseView, 1000 + 18)).toBe(80);
  });

  it("pins to 100 once the repair is reported complete", () => {
    const caseView = makeCase({ status: "REPAIRED", awarded, repaired_at: 1040, repair_progress_pct: 100 });
    expect(liveRepairProgress(caseView, 1041)).toBe(100);
  });

  it("falls back to the server value with no award", () => {
    expect(liveRepairProgress(makeCase({ repair_progress_pct: 0 }), 5000)).toBe(0);
  });
});

describe("stage coverage", () => {
  it("has a next step for every reachable status", () => {
    const statuses: CaseStatus[] = [...STAGE_ORDER];
    for (const status of statuses) {
      expect(nextStep(makeCase({ status })).label).toBeTruthy();
    }
  });
});
