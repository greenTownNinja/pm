import { expect, test } from "@playwright/test";
import { addCard, columns, deleteCard, signIn, uniqueTitle } from "./helpers";

test.beforeEach(async ({ page }) => {
  await signIn(page);
});

test("loads the kanban board", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(columns(page)).toHaveCount(5);
});

test("adds and deletes a card", async ({ page }) => {
  const title = uniqueTitle("Playwright card");
  const card = await addCard(page, columns(page).first(), title, "Added via e2e.");

  await expect(card).toBeVisible();
  await deleteCard(card, title);
});

test("edits a card", async ({ page }) => {
  const title = uniqueTitle("Editable");
  const card = await addCard(page, columns(page).first(), title, "Before.");

  const edited = `${title} edited`;
  await card.getByRole("button", { name: `Edit ${title}` }).click();
  await card.getByLabel("Edit title").fill(edited);
  await card.getByLabel("Edit details").fill("Details from e2e.");
  await card.getByRole("button", { name: /save card/i }).click();

  await expect(card.getByText(edited)).toBeVisible();
  await expect(card.getByText("Details from e2e.")).toBeVisible();
  await deleteCard(card, edited);
});

test("moves a card between columns", async ({ page }) => {
  const title = uniqueTitle("Draggable");
  const card = await addCard(
    page,
    columns(page).first(),
    title,
    "Moves across columns."
  );

  const target = columns(page).nth(3);
  const cardBox = await card.boundingBox();
  const columnBox = await target.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  // dnd-kit ignores instantaneous jumps, so the move is stepped.
  await page.mouse.move(columnBox.x + columnBox.width / 2, columnBox.y + 120, {
    steps: 12,
  });
  await page.mouse.up();

  await expect(target.getByText(title)).toBeVisible();
  await page.reload();
  await expect(columns(page).nth(3).getByText(title)).toBeVisible();
  await deleteCard(card, title);
});

test("every change survives a reload", async ({ page }) => {
  const title = uniqueTitle("Persistent");
  const card = await addCard(page, columns(page).first(), title, "Written to SQLite.");

  const edited = `${title} edited`;
  await card.getByRole("button", { name: `Edit ${title}` }).click();
  await card.getByLabel("Edit title").fill(edited);
  await card.getByRole("button", { name: /save card/i }).click();
  await expect(card.getByText(edited)).toBeVisible();

  await page.reload();
  await expect(card.getByText(edited)).toBeVisible();
  await expect(card.getByText("Written to SQLite.")).toBeVisible();

  await deleteCard(card, edited);
  await page.reload();
  await expect(card).toHaveCount(0);
});

test("a column rename survives a reload", async ({ page }) => {
  const columnTitle = () => columns(page).first().getByLabel("Column title");
  const original = await columnTitle().inputValue();
  const renamed = uniqueTitle("Ideas");

  // The rename is debounced, so wait for the request rather than racing the reload.
  const saved = page.waitForResponse(
    (response) =>
      response.request().method() === "PATCH" && response.url().includes("/api/columns/")
  );
  await columnTitle().fill(renamed);
  await saved;

  await page.reload();
  await expect(columnTitle()).toHaveValue(renamed);

  const restored = page.waitForResponse(
    (response) =>
      response.request().method() === "PATCH" && response.url().includes("/api/columns/")
  );
  await columnTitle().fill(original);
  await restored;
  await page.reload();
  await expect(columnTitle()).toHaveValue(original);
});
