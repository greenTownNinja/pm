import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";
import { addCard, columns, deleteCard, signIn, uniqueTitle } from "./helpers";

// Only meaningful when the app under test is the container, since it restarts it.
// Run with: PM_E2E_CONTAINER=1 npx playwright test restart
test.skip(
  !process.env.PM_E2E_CONTAINER,
  "set PM_E2E_CONTAINER=1 and run against a running pm-app container"
);

test("changes survive a container restart", async ({ page }) => {
  await signIn(page);
  const title = uniqueTitle("Survives restart");
  const card = await addCard(
    page,
    columns(page).first(),
    title,
    "In the pm-data volume."
  );

  execFileSync("docker", ["restart", "pm-app"], { stdio: "ignore" });
  await expect(async () => {
    const response = await page.request.get("/api/health");
    expect(response.ok()).toBe(true);
  }).toPass({ timeout: 30_000 });

  await page.reload();
  await expect(card).toBeVisible();
  await deleteCard(card, title);
});
