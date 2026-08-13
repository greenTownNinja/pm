import { expect, test } from "@playwright/test";
import { columns, deleteCard, signIn, uniqueTitle } from "./helpers";

// These turns call the real model, so they are slower and less exact than the rest of
// the suite. Assertions stay on what the board looks like afterwards.
test.describe.configure({ mode: "serial" });

test("asks the AI to add a card, and it persists", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page);

  const firstColumn = columns(page).first();
  const columnTitle = await firstColumn.getByLabel("Column title").inputValue();
  const title = uniqueTitle("AI card");

  await page.getByRole("button", { name: "Ask AI" }).click();
  // History is already on screen, so the new reply is one more than what is there.
  const replies = page.getByTestId("message-assistant");
  const repliesBefore = await replies.count();

  await page
    .getByLabel("Message")
    .fill(
      `Create a card titled "${title}" in the ${columnTitle} column. ` +
        `Leave everything else on the board alone.`
    );
  await page.getByRole("button", { name: "Send" }).click();

  // The reply and the new card both appear without a reload.
  await expect(replies).toHaveCount(repliesBefore + 1, { timeout: 90_000 });
  const card = firstColumn.locator('[data-testid^="card-"]').filter({ hasText: title });
  await expect(card).toHaveCount(1);

  await page.reload();
  await page.getByRole("button", { name: "Ask AI" }).click();

  // The conversation and the card both survived.
  await expect(page.getByText(title, { exact: false }).first()).toBeVisible();
  const reloaded = firstColumn
    .locator('[data-testid^="card-"]')
    .filter({ hasText: title });
  await expect(reloaded).toHaveCount(1);

  const testId = await reloaded.getAttribute("data-testid");
  await deleteCard(page.getByTestId(String(testId)), title);
});

test("answers a question without changing the board", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page);

  const before = await columns(page)
    .first()
    .locator('[data-testid^="card-"]')
    .count();

  await page.getByRole("button", { name: "Ask AI" }).click();
  const replies = page.getByTestId("message-assistant");
  const repliesBefore = await replies.count();

  await page.getByLabel("Message").fill("What is on my board?");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(replies).toHaveCount(repliesBefore + 1, { timeout: 90_000 });
  await expect(columns(page).first().locator('[data-testid^="card-"]')).toHaveCount(
    before
  );
});
