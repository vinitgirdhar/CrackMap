import { test, expect } from "@playwright/test";

test("selecting a benchmark sample renders real detection results", async ({ page }) => {
  await page.goto("/");

  await page.locator(".sample-select").first().selectOption({ index: 1 });

  await expect(page.locator(".latency-badge")).toContainText("ms", { timeout: 15000 });
  await expect(page.getByAltText("Original road frame")).toBeVisible();
  await expect(page.getByAltText("Annotated road frame")).toBeVisible();
});
