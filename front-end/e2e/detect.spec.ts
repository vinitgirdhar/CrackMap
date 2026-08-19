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
