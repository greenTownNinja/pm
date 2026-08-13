import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("the board is hidden until sign in", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("login-form")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeHidden();
});

test("wrong credentials show an error", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: /sign in/i }).click();
  // Scoped to the form: Next's route announcer is also role="alert".
  await expect(page.getByTestId("login-form").getByRole("alert")).toHaveText(
    "Invalid username or password"
  );
});

test("the session survives a reload and ends at sign out", async ({ page }) => {
  await signIn(page);

  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByRole("button", { name: /sign out/i }).click();
  await expect(page.getByTestId("login-form")).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("login-form")).toBeVisible();
});
