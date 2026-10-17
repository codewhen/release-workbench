import { test, expect } from "@playwright/test";

test("external workspace opens its child in Edit and Run without losing the parent draft", async ({
  page,
  request,
  context,
}) => {
  await page.goto("/workspace");
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const headers = { "X-Workbench-Token": token! };
  const child = await (
    await request.post("/api/create", {
      headers,
      data: {
        filename: "child-navigation.yaml",
        name: "Child navigation example",
      },
    })
  ).json();
  const parent = await (
    await request.post("/api/create", {
      headers,
      data: {
        filename: "parent-navigation.yaml",
        name: "Parent navigation example",
      },
    })
  ).json();
  const record = await (
    await request.get("/api/config?workflow=" + parent.id)
  ).json();
  record.workflow.graphs.main.cards.splice(1, 0, {
    id: "call",
    kind: "workspace",
    name: "Open nested workflow",
    config: { path: "child-navigation.yaml", inputs: {} },
  });
  const saved = await request.post("/api/save?workflow=" + parent.id, {
    headers,
    data: { workflow: record.workflow, revision: record.revision },
  });
  expect(saved.ok()).toBeTruthy();
  await page.goto("/workflows/" + parent.id + "/edit/list/cards/call");
  await page
    .getByLabel("Card name", { exact: true })
    .fill("Unsaved parent name");
  let opened = context.waitForEvent("page");
  await page
    .getByRole("button", { name: "Open child workflow", exact: true })
    .click();
  let childPage = await opened;
  await expect(childPage).toHaveURL(
    new RegExp("/workflows/" + child.id + "/edit$"),
  );
  await expect(
    childPage.getByRole("button", { name: "Edit", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await childPage.close();
  await expect(page.getByLabel("Card name", { exact: true })).toHaveValue(
    "Unsaved parent name",
  );
  await page.screenshot({
    path: "/private/tmp/workbench-child-navigation-edit.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Run", exact: true }).click();
  opened = context.waitForEvent("page");
  await page
    .getByRole("button", { name: "Open child workflow", exact: true })
    .click();
  childPage = await opened;
  await expect(childPage).toHaveURL(
    new RegExp("/workflows/" + child.id + "/run$"),
  );
  await expect(
    childPage.getByRole("button", { name: "Run", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await childPage.close();
  await page.screenshot({
    path: "/private/tmp/workbench-child-navigation-run.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Flowchart", exact: true }).click();
  await page.getByRole("button", { name: "Fit workflow", exact: true }).click();
  opened = context.waitForEvent("page");
  await page
    .locator(".flow-card.kind-workspace")
    .getByRole("button", { name: "Open child workflow", exact: true })
    .click();
  childPage = await opened;
  await expect(childPage).toHaveURL(
    new RegExp("/workflows/" + child.id + "/run$"),
  );
  await childPage.close();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await expect(page.getByLabel("Card name", { exact: true })).toHaveValue(
    "Unsaved parent name",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "/private/tmp/workbench-child-navigation-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  const stored = await (
    await request.get("/api/config?workflow=" + parent.id)
  ).json();
  expect(
    stored.workflow.graphs.main.cards.find(
      (card: { id: string }) => card.id === "call",
    ).name,
  ).toBe("Open nested workflow");
  await page
    .getByLabel("Workflow YAML path", { exact: true })
    .fill("missing-child.yaml");
  await page
    .getByRole("button", { name: "Open child workflow", exact: true })
    .click();
  await expect(
    page.locator(".workspace-navigation [role=alert]"),
  ).toBeVisible();
});
