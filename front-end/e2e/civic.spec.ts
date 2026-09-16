import { expect, test } from "@playwright/test";
import type { CaseView, Inspection, MapPoint, PipelineEvent, PipelineStats } from "../lib/types";

/**
 * Civic pipeline UI, driven entirely off mocked API routes.
 *
 * The backend's own pytest suite covers the stage machine; what needs proving
 * in a browser is that the workspace *renders* each stage correctly: the rail
 * counts, the live progress bar, the contextual action (never a "Next" button),
 * the tender board and the deliverables.
 */

const SECONDS_PER_SIM_DAY = 12;

function stats(overrides: Partial<PipelineStats> = {}): PipelineStats {
  return {
    total_findings: 2,
    unassigned_findings: 1,
    total_cases: 2,
    stage_counts: {
      DRAFT: 0,
      SUBMITTED: 1,
      ACKNOWLEDGED: 0,
      TENDERED: 1,
      WORK_ORDERED: 0,
      IN_REPAIR: 0,
      REPAIRED: 0,
      VERIFIED: 0,
      CLOSED: 0,
    },
    open_cases: 2,
    closed_cases: 0,
    sla_breached: 0,
    sla_at_risk: 1,
    potholes_reported: 7,
    potholes_repaired: 0,
    area_m2_reported: 3.4,
    estimated_inr: 9200,
    committed_inr: 0,
    seconds_per_sim_day: SECONDS_PER_SIM_DAY,
    stages: [],
    ...overrides,
  };
}

function finding(overrides: Partial<Inspection> = {}): Inspection {
  return {
    id: 11,
    filename: "frame_011.jpg",
    road_name: "Hill Road, Bandra West",
    lat: 19.0596,
    lon: 72.8295,
    address: "Hill Road, Bandra West, Mumbai, Maharashtra, India",
    ward: "Bandra West",
    city: "Mumbai",
    state: "Maharashtra",
    osm_road_type: "secondary",
    road_class: "Collector",
    total_defects: 3,
    severity_score: 4.1,
    composite_damage_score: 41,
    patch_area_m2: 2.6,
    priority: "P1",
    priority_label: "Critical — Safety Hazard",
    priority_score: 78.4,
    boxes: [],
    annotated_image: "",
    created_at: Date.now() / 1000 - 30,
    case_id: null,
    ...overrides,
  };
}

function caseView(overrides: Partial<CaseView> = {}): CaseView {
  const now = Date.now() / 1000;
  return {
    id: 4,
    status: "TENDERED",
    stage_index: 3,
    stage_label: "Tender & Bidding",
    created_at: now - 120,
    total_potholes: 4,
    avg_severity: 4.2,
    severity_label: "Severe",
    severity_hex: "#ef4444",
    priority: "P1",
    priority_label: "Critical — Safety Hazard",
    priority_score: 81.2,
    patch_area_m2: 2.4,
    estimate_inr: 6900,
    boq: {
      area_m2: 2.4,
      lines: [
        {
          description: "Bituminous concrete hot-mix patch, 50 mm compacted",
          unit: "m²",
          quantity: 2.4,
          rate_inr: 1450,
          amount_inr: 3480,
        },
      ],
      subtotal_inr: 3480,
      net_inr: 3932,
      gst_inr: 708,
      total_inr: 6900,
    },
    portal: {
      code: "MCGM",
      name: "MCGM Pothole Fixit — Voice of Citizen",
      authority: "Brihanmumbai Municipal Corporation",
      department: "Roads & Traffic Department",
      portal_url: "https://portal.mcgm.gov.in",
      simulated: true,
    },
    tracking_id: "MCGM/RTD/2026/00042",
    routing_note: "Coordinate falls inside the Brihanmumbai Municipal Corporation municipal limit.",
    officer: "Ward Engineer — R. Shaikh",
    submitted_at: now - 90,
    acknowledged_at: now - 84,
    sla_hours: 24,
    sla_due_at: now + 6,
    sla_state: "AT_RISK",
    hours_remaining: 12,
    breached: false,
    tendered_at: now - 20,
    bids: [
      {
        contractor_id: 3,
        contractor_name: "SafeStreet Civil Works",
        specialty: "Emergency 24h repair",
        service_area: "Powai, Ghatkopar, Kurla",
        rating: 4.7,
        quoted_inr: 6100,
        variance_pct: -11.6,
        promised_days: 2,
      },
      {
        contractor_id: 1,
        contractor_name: "Konkan Asphalt & Paving Co.",
        specialty: "Hot-mix pothole patching",
        service_area: "Bandra, Andheri, Santacruz",
        rating: 4.4,
        quoted_inr: 7400,
        variance_pct: 7.2,
        promised_days: 3,
      },
    ],
    awarded: null,
    repair_progress_pct: 0,
    repair_sim_days: 0,
    repaired_at: null,
    verification: null,
    verified_at: null,
    closed_at: null,
    seconds_per_sim_day: SECONDS_PER_SIM_DAY,
    findings: [
      {
        id: 9,
        filename: "frame_009.jpg",
        road_name: "Hill Road, Bandra West",
        address: "Hill Road, Bandra West, Mumbai",
        ward: "Bandra West",
        city: "Mumbai",
        road_class: "Collector",
        lat: 19.0596,
        lon: 72.8295,
        total_defects: 4,
        severity_score: 4.2,
        composite_damage_score: 38,
        patch_area_m2: 2.4,
        priority: "P1",
        created_at: now - 130,
        case_id: 4,
        boxes: [],
        annotated_image: "",
      },
    ],
    events: [
      {
        id: 1,
        case_id: 4,
        inspection_id: null,
        stage: "DRAFT",
        actor: "CrackMap Triage Engine",
        title: "Case #4 opened — P1 Critical — Safety Hazard",
        detail: "1 finding, 4 potholes across 2.4 m².",
        created_at: now - 120,
      },
      {
        id: 2,
        case_id: 4,
        inspection_id: null,
        stage: "ACKNOWLEDGED",
        actor: "MCGM Pothole Fixit — Voice of Citizen",
        title: "Grievance acknowledged — assigned to Ward Engineer — R. Shaikh",
        detail: "Committed to a 24-hour response window.",
        created_at: now - 84,
      },
    ],
    ...overrides,
  };
}

const events: PipelineEvent[] = caseView().events;

const mapPoints: MapPoint[] = [
  {
    id: 9,
    road_name: "Hill Road, Bandra West",
    address: "Hill Road, Bandra West, Mumbai, Maharashtra, India",
    ward: "Bandra West",
    road_class: "Collector",
    lat: 19.0596,
    lon: 72.8295,
    total_defects: 4,
    severity: "Severe",
    severity_score: 4.2,
    confidence: 0.91,
    damage_score: 38,
    priority: "P1",
    color_hex: "#ef4444",
    color_r: 239,
    color_g: 68,
    color_b: 68,
    case_id: 4,
    case_status: "TENDERED",
    tracking_id: "MCGM/RTD/2026/00042",
    repaired: false,
    logged_at: Date.now() / 1000 - 130,
  },
];

async function mockPipeline(
  page: import("@playwright/test").Page,
  cases: CaseView[],
  pipelineStats = stats()
) {
  await page.route("**/api/civic/stats", (route) =>
    route.fulfill({ json: pipelineStats })
  );
  await page.route("**/api/civic/cases", (route) => route.fulfill({ json: cases }));
  await page.route("**/api/civic/cases/*", (route) =>
    route.fulfill({ json: cases[0] })
  );
  await page.route("**/api/civic/events**", (route) => route.fulfill({ json: events }));
  await page.route("**/api/inspections", (route) => route.fulfill({ json: [finding()] }));
  await page.route("**/api/gis-data", (route) => route.fulfill({ json: mapPoints }));
  // Keep the real tile server out of the test run.
  await page.route(/tile\.openstreetmap\.org|basemaps\.cartocdn\.com|arcgisonline\.com/, (route) =>
    route.abort()
  );
}

test("pipeline board shows live stage counts, the intake queue and the map", async ({ page }) => {
  await mockPipeline(page, [caseView()]);
  await page.goto("/");
  await page.locator("#pill-civic").click();

  // KPI strip reflects the stats payload, not placeholders.
  const kpis = page.locator(".civic-kpi-strip");
  await expect(kpis).toContainText("Findings logged");
  await expect(kpis).toContainText("Committed spend");

  // Stage rail carries a count on the stages that hold cases.
  const rail = page.locator(".stage-rail");
  await expect(rail.locator(".stage-node")).toHaveCount(9);
  await expect(rail.locator(".stage-node.has-cases")).toHaveCount(2);
  await expect(page.locator(".stage-rail-all")).toContainText("2");

  // Stages the backend advances by itself are labelled as automatic.
  await expect(rail).toContainText("auto");

  // Intake queue lists the unassigned finding with its triage output.
  const intake = page.locator(".civic-panel", { hasText: "Intake queue" });
  await expect(intake).toContainText("Hill Road, Bandra West");
  await expect(intake).toContainText("Collector");
  await expect(intake).toContainText("P1");

  // Map is live and wired to real coordinates.
  await expect(page.locator(".map-live-badge")).toContainText("updated");
  await expect(page.locator(".gis-map-container")).toBeVisible();
  await expect(page.locator(".map-legend")).toContainText("Severity (fill)");
  await expect(page.locator(".gis-map-empty")).toHaveCount(0);

  // Live activity feed renders persisted audit events.
  const feed = page.locator(".live-feed");
  await expect(feed).toContainText("Grievance acknowledged");
  await expect(feed).toContainText("MCGM Pothole Fixit");
});

test("stage rail filters the case board", async ({ page }) => {
  await mockPipeline(page, [caseView()]);
  await page.goto("/");
  await page.locator("#pill-civic").click();

  await expect(page.locator(".case-card")).toHaveCount(1);

  // Filter to a stage the single case is not in.
  await page.locator(".stage-node", { hasText: "Closed" }).click();
  await expect(page.locator(".case-card")).toHaveCount(0);
  await expect(page.locator(".civic-empty")).toContainText("Nothing at this stage");

  await page.locator(".stage-rail-all").click();
  await expect(page.locator(".case-card")).toHaveCount(1);
});

test("a tendered case opens a drawer with bids, filing record and deliverables", async ({ page }) => {
  await mockPipeline(page, [caseView()]);
  await page.goto("/");
  await page.locator("#pill-civic").click();

  await page.locator(".case-card").first().click();
  const drawer = page.locator(".case-drawer");
  await expect(drawer).toBeVisible();

  // The action is named for what it does — never "Next".
  const banner = drawer.locator(".next-step-banner");
  await expect(banner).toContainText("Award the work order");
  await expect(banner).not.toContainText("Next");
  // Awarding happens per-bid below, so the banner points there instead of
  // duplicating the control.
  await expect(banner.locator(".primary-pill-btn")).toContainText("Compare bids");

  // Municipal filing record, flagged as simulated.
  await expect(drawer).toContainText("Brihanmumbai Municipal Corporation");
  await expect(drawer).toContainText("MCGM/RTD/2026/00042");
  await expect(drawer).toContainText("Ward Engineer — R. Shaikh");
  await expect(drawer.locator(".sim-badge")).toContainText("simulated filing");

  // Tender board ranks the bids and offers a real choice per contractor.
  const bidRows = drawer.locator(".bid-table tbody tr");
  await expect(bidRows).toHaveCount(2);
  await expect(bidRows.first()).toContainText("SafeStreet Civil Works");
  await expect(bidRows.first()).toContainText("lowest");
  await expect(drawer.locator(".bid-table tbody button")).toHaveCount(2);

  // Priced bill of quantities with tax.
  await expect(drawer).toContainText("Bill of quantities");
  await expect(drawer.locator(".boq-total")).toContainText("₹6,900");

  // Audit trail and deliverables.
  await expect(drawer.locator(".audit-timeline li")).toHaveCount(2);
  const deliverables = drawer.locator(".deliverables-row");
  await expect(deliverables).toContainText("Case dossier");
  await expect(deliverables).toContainText("Defect inventory");
  // The certificate stays locked until a re-inspection passes.
  await expect(deliverables.locator(".deliverable-card.is-locked")).toContainText(
    "Completion certificate"
  );

  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
});

test("an in-repair case shows a live progress bar instead of a button", async ({ page }) => {
  const now = Date.now() / 1000;
  const repairing = caseView({
    status: "IN_REPAIR",
    stage_index: 5,
    stage_label: "Repair In Progress",
    repair_progress_pct: 35,
    awarded: {
      contractor_id: 3,
      contractor_name: "SafeStreet Civil Works",
      specialty: "Emergency 24h repair",
      rating: 4.7,
      crew_count: 4,
      awarded_inr: 6100,
      promised_days: 2,
      variance_pct: -11.6,
      awarded_at: now - 18,
    },
  });
  await mockPipeline(page, [repairing]);
  await page.goto("/");
  await page.locator("#pill-civic").click();

  // The card carries a progress bar and the crew name.
  const card = page.locator(".case-card").first();
  await expect(card.locator(".case-progress-fill")).toBeVisible();
  await expect(card).toContainText("SafeStreet");

  await card.click();
  const drawer = page.locator(".case-drawer");
  await expect(drawer.locator(".next-step-banner.kind-waiting")).toContainText("Repair underway");
  // No action button on a stage the backend drives itself.
  await expect(drawer.locator(".next-step-banner .primary-pill-btn")).toHaveCount(0);
  await expect(drawer.locator(".waiting-badge")).toContainText("%");
  await expect(drawer.locator(".repair-progress-block")).toContainText("4-person crew");
});

test("a verified case exposes the completion certificate", async ({ page }) => {
  const now = Date.now() / 1000;
  const verified = caseView({
    status: "VERIFIED",
    stage_index: 7,
    stage_label: "Re-Inspection Passed",
    sla_state: "MET",
    repaired_at: now - 20,
    verified_at: now - 5,
    awarded: {
      contractor_id: 3,
      contractor_name: "SafeStreet Civil Works",
      specialty: "Emergency 24h repair",
      rating: 4.7,
      crew_count: 4,
      awarded_inr: 6100,
      promised_days: 2,
      variance_pct: -11.6,
      awarded_at: now - 60,
    },
    verification: {
      filename: "after.jpg",
      defects_before: 4,
      defects_after: 1,
      remaining_ratio: 0.25,
      effectiveness_pct: 75,
      severity_after: 1.5,
      damage_score_after: 86,
      annotated_image: "",
      passed: true,
      checked_at: now - 5,
      attempts: 1,
    },
  });
  await mockPipeline(page, [verified]);
  await page.goto("/");
  await page.locator("#pill-civic").click();

  await expect(page.locator(".case-card-verify.passed")).toContainText("Re-inspection passed");

  await page.locator(".case-card").first().click();
  const drawer = page.locator(".case-drawer");
  await expect(drawer.locator(".next-step-banner")).toContainText("Close case & issue certificate");
  await expect(drawer.locator(".next-step-banner .primary-pill-btn")).toContainText("Close & certify");
  await expect(drawer.locator(".verify-result.passed")).toContainText("Re-inspection passed");
  await expect(drawer.locator(".verify-metrics")).toContainText("75%");

  const certificate = drawer.locator(".deliverable-card", { hasText: "Completion certificate" });
  await expect(certificate).not.toHaveClass(/is-locked/);
  await expect(certificate).toHaveAttribute("href", "/api/civic/cases/4/certificate.pdf");
});

test("the map states plainly that it has no demo pins", async ({ page }) => {
  await mockPipeline(page, [], stats({ total_cases: 0, total_findings: 0, unassigned_findings: 0 }));
  await page.route("**/api/gis-data", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/inspections", (route) => route.fulfill({ json: [] }));
  await page.goto("/");
  await page.locator("#pill-civic").click();

  await expect(page.locator(".gis-map-empty")).toContainText("No geotagged findings yet");
  await expect(page.locator(".gis-map-empty")).toContainText("no demo pins");
});
