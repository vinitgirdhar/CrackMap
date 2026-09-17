import { expect, test } from "@playwright/test";
import type { CitizenCaseView, DetectionResult } from "../lib/types";

/**
 * The public citizen surface at /report, driven entirely off mocked API
 * routes. Backend correctness (stage collapsing, the server-side leak check
 * on contractor/cost) is covered by the pytest suite; what needs proving
 * here is that the page renders the citizen-safe projection correctly and
 * never surfaces anything the API didn't send it in the first place.
 */

function detection(overrides: Partial<DetectionResult> = {}): DetectionResult {
  return {
    success: true,
    inference_time_ms: 42,
    total_defects: 2,
    severity_score: 3.5,
    composite_damage_score: 55,
    boxes: [],
    annotated_image: "data:image/jpeg;base64,AAAA",
    original_image: "data:image/jpeg;base64,BBBB",
    road_mask: "",
    ...overrides,
  };
}

const CASE_ID = 21;

function citizenCase(overrides: Partial<CitizenCaseView> = {}): CitizenCaseView {
  const now = Date.now() / 1000;
  const stageKeys = [
    "REPORTED",
    "FILED",
    "UNDER_REVIEW",
    "REPAIR_ASSIGNED",
    "REPAIR_IN_PROGRESS",
    "VERIFYING",
    "RESOLVED",
  ] as const;
  const labels: Record<string, string> = {
    REPORTED: "Reported",
    FILED: "Filed with the Authority",
    UNDER_REVIEW: "Under Review",
    REPAIR_ASSIGNED: "Repair Team Assigned",
    REPAIR_IN_PROGRESS: "Repair In Progress",
    VERIFYING: "Verifying Repair",
    RESOLVED: "Resolved",
  };
  const descriptions: Record<string, string> = {
    REPORTED: "Your report was received and logged for review.",
    FILED: "Routed to the municipal department responsible for this road.",
    UNDER_REVIEW: "A municipal officer has acknowledged the report and is reviewing it.",
    REPAIR_ASSIGNED: "A repair crew has been assigned to fix this road.",
    REPAIR_IN_PROGRESS: "The crew is on site carrying out the repair.",
    VERIFYING: "The repair is complete and is being inspected.",
    RESOLVED: "The repair has been verified and the case is closed.",
  };
  const activeKey = overrides.stages ? null : "REPORTED";
  const activeIdx = activeKey ? stageKeys.indexOf(activeKey as (typeof stageKeys)[number]) : -1;

  return {
    case_id: CASE_ID,
    tracking_id: null,
    status: "DRAFT",
    authority: null,
    department: null,
    road_name: "Hill Road, Bandra West",
    address: "Hill Road, Bandra West, Mumbai, Maharashtra, India",
    lat: 19.0596,
    lon: 72.8295,
    total_potholes: 2,
    patch_area_m2: 1.1,
    priority: "P2",
    priority_label: "High",
    reported_at: now - 60,
    stages: stageKeys.map((key, i) => ({
      key,
      label: labels[key],
      description: descriptions[key],
      completed: activeIdx >= 0 ? i < activeIdx : false,
      active: activeIdx >= 0 ? i === activeIdx : false,
      at: activeIdx >= 0 && i <= activeIdx ? now - (stageKeys.length - i) * 30 : null,
    })),
    is_resolved: false,
    before_image: "",
    after_image: "",
    description: null,
    fix_summary: null,
    ...overrides,
  };
}

async function mockDetectAndReport(page: import("@playwright/test").Page) {
  await page.route("**/api/samples", (route) => route.fulfill({ json: { samples: ["1.jpg", "2.jpg"] } }));
  await page.route("**/api/detect", (route) => route.fulfill({ json: detection() }));
  await page.route("**/api/inspections", (route) => route.fulfill({ json: { id: 55 } }));
  await page.route("**/api/civic/cases", (route) => route.fulfill({ json: { id: CASE_ID, status: "DRAFT" } }));
  await page.route(`**/api/civic/cases/${CASE_ID}/submit`, (route) =>
    route.fulfill({ json: { id: CASE_ID, status: "SUBMITTED" } })
  );
}

async function mockCitizenCase(page: import("@playwright/test").Page, view: CitizenCaseView) {
  await page.route(`**/api/civic/cases/${CASE_ID}/citizen`, (route) => route.fulfill({ json: view }));
}

// Text that must never appear on the citizen page under any stage.
const SENSITIVE_STRINGS = [
  "₹",
  "Rs ",
  "SafeStreet",
  "Konkan Asphalt",
  "MumbaiRoad",
  "Maharashtra Pavement",
  "GreenLine",
  "contractor",
  "Contractor",
  "estimate",
  "Estimate",
  "quote",
  "Quote",
  "bid",
  "Bid",
];

async function assertNoSensitiveLeak(page: import("@playwright/test").Page) {
  const body = await page.locator("body").innerText();
  for (const leak of SENSITIVE_STRINGS) {
    expect(body, `leaked "${leak}"`).not.toContain(leak);
  }
}

test("citizen can upload a photo, detect damage, confirm a location and submit a report", async ({
  page,
}) => {
  await mockDetectAndReport(page);
  await mockCitizenCase(page, citizenCase());

  await page.goto("/report");
  await expect(page.locator(".citizen-step-badge").first()).toContainText("Step 1 of 2");

  await page.locator(".citizen-sample-picker select").selectOption("1.jpg");
  await expect(page.locator(".latency-badge")).toContainText("2 potholes");

  await expect(page.locator(".citizen-locate-section")).toBeVisible();
  await page.locator(".citizen-locate-section input[type=text]").first().fill("Hill Road, Bandra West");

  await page.locator(".citizen-submit-btn").click();

  await expect(page).toHaveURL(new RegExp(`case=${CASE_ID}`));
  await expect(page.locator(".citizen-tracker")).toBeVisible();
  await expect(page.locator(".citizen-road-row")).toContainText("Hill Road, Bandra West");
});

test("zero detected potholes blocks submission with a friendly message, not an error", async ({ page }) => {
  await page.route("**/api/samples", (route) => route.fulfill({ json: { samples: ["1.jpg"] } }));
  await page.route("**/api/detect", (route) => route.fulfill({ json: detection({ total_defects: 0 }) }));

  await page.goto("/report");
  await page.locator(".citizen-sample-picker select").selectOption("1.jpg");

  await expect(page.locator(".citizen-no-defects")).toContainText("couldn");
  await expect(page.locator(".citizen-locate-section")).toHaveCount(0);
});

test("tracker renders a plain-language timeline with zero contractor or cost information", async ({
  page,
}) => {
  // TENDERED collapses to "Under Review" on the citizen side — no contractor
  // has been picked yet, so nothing reads as "assigned".
  const view = citizenCase({
    status: "TENDERED",
    tracking_id: "MCGM/RTD/2026/00021",
    authority: "Brihanmumbai Municipal Corporation",
    department: "Roads & Traffic Department",
  });
  view.stages = view.stages.map((s, i) => ({
    ...s,
    active: s.key === "UNDER_REVIEW",
    completed: i < 2,
  }));
  await mockCitizenCase(page, view);

  await page.goto(`/report?case=${CASE_ID}`);

  await expect(page.locator(".citizen-tracking-id")).toContainText("MCGM/RTD/2026/00021");
  await expect(page.locator(".citizen-authority-row")).toContainText("Brihanmumbai Municipal Corporation");

  const timeline = page.locator(".citizen-timeline");
  await expect(timeline).toContainText("Under Review");
  await expect(timeline).toContainText("A municipal officer has acknowledged");
  await expect(timeline.locator("li.is-active")).toContainText("Under Review");
  await expect(timeline.locator("li.is-done")).toHaveCount(2); // Reported, Filed

  await assertNoSensitiveLeak(page);
});

test("a resolved case shows before/after evidence and a cost-free fix summary", async ({ page }) => {
  const view = citizenCase({
    status: "CLOSED",
    tracking_id: "MCGM/RTD/2026/00021",
    authority: "Brihanmumbai Municipal Corporation",
    is_resolved: true,
    before_image: "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBTAA7",
    after_image: "data:image/gif;base64,R0lGODlhAQABAIAAAP8AAAAAACH5BAEAAAAALAAAAAABAAEAAAICTAEAOw==",
    description:
      "The reported damage on Hill Road, Bandra West has been repaired and verified by an AI " +
      "re-inspection, clearing 100% of the originally detected damage.",
    fix_summary: "Patched 2 potholes across 1.1 m² on Hill Road, Bandra West.",
  });
  view.stages = view.stages.map((s) => ({ ...s, completed: s.key !== "RESOLVED", active: s.key === "RESOLVED" }));
  await mockCitizenCase(page, view);

  await page.goto(`/report?case=${CASE_ID}`);

  const resolved = page.locator(".citizen-resolved");
  await expect(resolved).toBeVisible();
  await expect(resolved.locator(".completed-evidence-pane img")).toHaveCount(2);
  await expect(resolved).toContainText("100% of the originally detected damage");
  await expect(page.locator(".citizen-fix-summary")).toContainText(
    "Patched 2 potholes across 1.1 m² on Hill Road, Bandra West."
  );

  await assertNoSensitiveLeak(page);

  // Reporting another pothole clears the URL and returns to the form.
  await page.locator(".citizen-report-another").click();
  await expect(page).toHaveURL(/\/report$/);
  await expect(page.locator(".citizen-step-badge").first()).toContainText("Step 1 of 2");
});

test("an unknown tracking link shows a friendly not-found state", async ({ page }) => {
  await page.route("**/api/civic/cases/999999/citizen", (route) =>
    route.fulfill({ status: 404, json: { detail: "Case 999999 not found" } })
  );

  await page.goto("/report?case=999999");

  await expect(page.locator(".citizen-notfound")).toBeVisible();
  await expect(page.locator(".citizen-notfound")).toContainText("couldn");
  await expect(page.locator(".citizen-notfound .citizen-submit-btn")).toBeVisible();
});
