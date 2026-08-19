import { test, expect } from "@playwright/test";

test("selecting a benchmark sample renders real detection results and methodology", async ({ page }) => {
  await page.goto("/");

  // Check top stat strip shows real training corpus stats
  await expect(page.locator(".hero-metrics-row")).toContainText("Training Corpus");
  await expect(page.locator(".hero-metrics-row")).toContainText("Dataset Potholes");
  await expect(page.locator(".hero-metrics-row")).not.toContainText("Surveyed Area");
  await expect(page.locator(".hero-metrics-row")).not.toContainText("Verified Pavement");

  // Select sample 1
  await page.locator(".sample-select").first().selectOption({ index: 1 });

  // Verification of detection latency and composite score
  await expect(page.locator(".latency-badge")).toContainText("ms", { timeout: 15000 });
  await expect(page.locator(".latency-badge")).toContainText("Damage Score:");
  await expect(page.getByAltText("Original road frame")).toBeVisible();
  await expect(page.getByAltText("Annotated road frame")).toBeVisible();

  // Verify methodology panel is visible with formula
  const methodologyCard = page.locator(".methodology-card");
  await expect(methodologyCard).toBeVisible();
  await expect(methodologyCard).toContainText("How Damage Scores and Severity Bands Are Calculated");
  await expect(methodologyCard).toContainText("composite_damage_score = max(15, 100");
  await expect(methodologyCard).toContainText("ASTM D6433");
});

test("refresh button, filter controls, settings modal, and dataset analytics tab", async ({ page }) => {
  await page.goto("/");

  // 1. Test Refresh Button
  const refreshBtn = page.locator(".refresh-btn");
  await expect(refreshBtn).toBeVisible();
  await refreshBtn.click();
  await expect(page.locator(".top-nav-bar")).toBeVisible();

  // 2. Test Filter Controls Popover (Confidence Icon & Threshold)
  const filterBtn = page.locator('button[aria-label="Inspection and filter controls"]');
  await filterBtn.click();
  const filterPopover = page.locator(".filter-popover-card");
  await expect(filterPopover).toBeVisible();
  await expect(filterPopover).toContainText("Confidence Threshold");
  await expect(filterPopover).toContainText("Minimum AI model detection certainty");
  await page.keyboard.press("Escape");

  // 3. Test Settings Modal (Backend Endpoint Removed)
  const settingsBtn = page.locator('button[aria-label="System settings"]');
  await settingsBtn.click();
  const settingsModal = page.locator(".settings-modal-card");
  await expect(settingsModal).toBeVisible();
  await expect(settingsModal).toContainText("Display & Telemetry Preferences");
  await expect(settingsModal).not.toContainText("Backend REST API Endpoint");
  await page.keyboard.press("Escape");

  // 4. Test Dataset Analytics Tab
  await page.locator("#pill-analytics").click();
  await expect(page.getByText("Benchmark Dataset Profile")).toBeVisible();
  await expect(page.getByText("chitholian/annotated-potholes-dataset")).toBeVisible();
  await expect(page.getByText("Dataset Partitioning & Splits")).toBeVisible();
  await expect(page.getByText("Trained YOLOv8s Model Performance")).toBeVisible();
});
