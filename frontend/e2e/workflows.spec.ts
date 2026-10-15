import { test, expect, type Page } from "@playwright/test";
async function open(page: Page, name: string) {
  await page.goto("/");
  await page
    .locator(".workflow-row")
    .filter({ has: page.getByRole("heading", { name, exact: true }) })
    .getByRole("button", { name: "Open workflow" })
    .click();
  await expect(
    page.getByRole("button", { name: "Run all", exact: true }),
  ).toBeVisible();
}
async function choose(page: Page, label: string, value: string) {
  await page.getByRole("combobox", { name: label, exact: true }).click();
  await page.getByRole("option", { name: value, exact: true }).click();
}
async function connectTo(page: Page, source: string, target: string) {
  await page.locator(`[data-card-id="${source}"]`).click();
  await choose(page, "Connect to card", target);
  await page
    .getByRole("button", { name: "Connect execution", exact: true })
    .click();
}
test("ten-step flowchart can be built, saved, reloaded and run entirely in the browser", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New workflow", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Ten steps");
  await page.getByLabel("Filename", { exact: true }).fill("ten-steps.yaml");
  await page
    .getByRole("button", { name: "Create workflow", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  for (let n = 1; n <= 10; n++) {
    await page
      .getByRole("button", { name: "Add card", exact: true })
      .first()
      .click();
    await page.getByRole("menuitem", { name: "Wait", exact: true }).click();
    await page.getByLabel("Card name", { exact: true }).fill("Wait " + n);
    await page.getByLabel("Seconds", { exact: true }).fill("0");
  }
  await connectTo(page, "start", "Wait 1");
  for (let n = 1; n <= 10; n++)
    await connectTo(page, "card-" + n, n === 10 ? "Finish" : "Wait " + (n + 1));
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("saved");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Run all", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  await expect(page.locator("aside")).toContainText("12 passed");
});
test("functions, repeated manual decisions and run inspection", async ({
  page,
}) => {
  await open(page, "Manual Boolean decision");
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator('[data-card-id="decision"]').click();
  await page
    .getByRole("button", { name: "Open function", exact: true })
    .click();
  await expect(
    page.getByRole("navigation", { name: "Function navigation" }),
  ).toContainText("returns boolean");
  await page
    .getByRole("button", { name: "Back to caller", exact: true })
    .click();
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await expect(
    page.getByRole("dialog", { name: "Action required" }),
  ).toBeVisible();
  await choose(page, "Return Boolean", "True");
  await page.getByLabel("Evidence notes").fill("Browser verified");
  await page
    .getByRole("button", { name: "Return result and continue" })
    .click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
});
test("manual prompts reopen on a new run and can return False successfully", async ({
  page,
}) => {
  await open(page, "Manual Boolean decision");
  for (const answer of ["False", "True"]) {
    await page.getByRole("button", { name: "Run all", exact: true }).click();
    await expect(
      page.getByRole("dialog", { name: "Action required" }),
    ).toBeVisible();
    await choose(page, "Return Boolean", answer);
    await page.getByLabel("Evidence notes").fill("Verified " + answer);
    await page
      .getByRole("button", { name: "Return result and continue" })
      .click();
    await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  }
});

test("live Stop cancels a pending poll", async ({ page }) => {
  await open(page, "Poll for a file");
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await expect(page.locator(".toolbar .status.running")).toBeVisible();
  await page.getByRole("button", { name: "Stop all", exact: true }).click();
  await expect(page.locator(".toolbar .status.cancelled")).toBeVisible();
});
test("context actions, undo, primary editing and layout-only areas", async ({
  page,
}) => {
  await open(page, "While with a Boolean function");
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator('[data-card-id="start"]').click({ button: "right" });
  await expect(
    page.getByRole("menuitem", { name: "Duplicate card", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("menu").press("Escape");
  await page.locator('[data-card-id="increment"]').click({ button: "right" });
  await page
    .getByRole("menuitem", { name: "Duplicate card", exact: true })
    .click();
  await expect(page.locator("[data-card-id]")).toHaveCount(5);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(page.locator("[data-card-id]")).toHaveCount(4);
  await page.getByRole("button", { name: "Redo", exact: true }).click();
  await expect(page.locator("[data-card-id]")).toHaveCount(5);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await page
    .getByRole("button", { name: "Add card", exact: true })
    .first()
    .click();
  await page
    .getByRole("menuitem", { name: "Collapsible area", exact: true })
    .click();
  await page.getByRole("button", { name: "Flowchart", exact: true }).click();
  await expect(page.locator(".layout-area")).toBeVisible();
  await page
    .getByRole("button", { name: "Collapse area", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Expand area", exact: true }),
  ).toBeVisible();
});
test("mobile List and custom dropdowns stay inside viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, "While with a Boolean function");
  await expect(
    page.getByRole("region", { name: "Flowchart cards" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.locator('[data-card-id="repeat"]').click();
  await choose(page, "Loop mode", "count");
  await expect(page.getByLabel("Repeat count", { exact: true })).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator("select")).toHaveCount(0);
});

test("invalid JSON cannot silently save its previous value", async ({
  page,
}) => {
  await open(page, "Python return and file output");
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator('[data-card-id="compute"]').click();
  await choose(page, "message source", "A value I enter");
  await page.getByLabel("message value", { exact: true }).fill("broken JSON");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.locator(".alert.error")).toContainText(
    "Fix invalid fields",
  );
  await page.getByLabel("message value", { exact: true }).fill('"safe value"');
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("saved");
});
