import { expect, type Locator, type Page } from "@playwright/test";

/** Signs in with the hardcoded MVP credentials and waits for the board. */
export const signIn = async (page: Page) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
};

export const columns = (page: Page) => page.locator('[data-testid^="column-"]');

/**
 * The board is persistent now, so specs work on their own card rather than the seeded
 * ones, and clean it up afterwards.
 */
export const uniqueTitle = (prefix: string) => `${prefix} ${Date.now()}`;

const byText = (page: Page, title: string) =>
  page.locator('[data-testid^="card-"]').filter({ hasText: title });

/**
 * Adds a card and returns a locator keyed on its server id. Locating by text breaks the
 * moment the card is edited, because the title moves into an input value.
 */
export const addCard = async (
  page: Page,
  column: Locator,
  title: string,
  details: string
): Promise<Locator> => {
  await column.getByRole("button", { name: /add a card/i }).click();
  await column.getByPlaceholder("Card title").fill(title);
  await column.getByPlaceholder("Details").fill(details);
  await column.getByRole("button", { name: /add card/i }).click();

  const created = byText(page, title);
  await expect(created).toHaveCount(1);
  const testId = await created.getAttribute("data-testid");
  return page.getByTestId(String(testId));
};

export const deleteCard = async (card: Locator, title: string) => {
  await card.getByRole("button", { name: `Delete ${title}` }).click();
  await expect(card).toHaveCount(0);
};
