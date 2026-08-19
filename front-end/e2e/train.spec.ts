import { test, expect } from "@playwright/test";

// Mocks the backend routes so this doesn't run a real multi-epoch job in CI.
test("starting a training run polls status and reflects progress through to completion", async ({ page }) => {
  let pollCount = 0;

  await page.route("**/api/train-model", (route) =>
    route.fulfill({ json: { success: true, message: "started", epochs: 5, architecture: "fasterrcnn_mobilenet" } })
  );

  await page.route("**/api/train-status", (route) => {
    pollCount += 1;
    if (pollCount < 2) {
      return route.fulfill({
        json: {
          status: "training",
          progress: 0.2 * pollCount,
          current_epoch: pollCount,
          total_epochs: 5,
          current_loss: 1.0,
          losses: [{ epoch: pollCount, loss: 1.0 }],
          checkpoint_path: "",
          error: null,
        },
      });
    }
    return route.fulfill({
      json: {
        status: "completed",
        progress: 1,
        current_epoch: 5,
        total_epochs: 5,
        current_loss: 0.2,
        losses: [{ epoch: 5, loss: 0.2 }],
        checkpoint_path: "custom_fine_tuned_detector.pth",
        error: null,
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Train Model" }).click();
  await page.getByRole("button", { name: /Start Real Model Fine-Tuning/ }).click();

  await expect(page.locator(".train-progress-fill")).toBeVisible({ timeout: 5000 });
  await expect(page.getByText("Fine-Tuning Complete")).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(/custom_fine_tuned_detector\.pth/)).toBeVisible();
});
