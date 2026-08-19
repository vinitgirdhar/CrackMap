import { test, expect } from "@playwright/test";

test("GIS tab renders the Leaflet map with one marker per /api/gis-data point", async ({ page, request }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "GIS CrackMap" }).click();

  await expect(page.locator(".leaflet-container")).toBeVisible();

  const gisData = await (await request.get("/api/gis-data")).json();
  await expect(page.locator(".leaflet-interactive")).toHaveCount(gisData.length, { timeout: 10000 });
});
