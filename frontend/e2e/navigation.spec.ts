import { readRoute } from "../src/navigation/location";
import {
  test,
  expect,
  type Page,
  type APIRequestContext,
} from "@playwright/test";

async function fixture(
  page: Page,
  request: APIRequestContext,
  filename: string,
) {
  await page.goto("/");
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const headers = { "X-Workbench-Token": token! };
  const entry = await (
    await request.post("/api/create", {
      headers,
      data: { filename, name: "Navigation example", template: "python" },
    })
  ).json();
  return { entry, headers };
}

test("workspace is default; folder links survive reload and Back/Forward", async ({
  page,
  request,
}) => {
  const { entry, headers } = await fixture(
    page,
    request,
    "navigation-folders.yaml",
  );
  const folders = page.getByRole("navigation", { name: "Workflow folders" });
  await expect(
    folders.getByRole("button", { name: "My workspace", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await request.post("/api/organize", {
    headers,
    data: { action: "new_folder", name: "Navigation" },
  });
  await request.post("/api/organize", {
    headers,
    data: { action: "new_folder", name: "Nested", parent: "Navigation" },
  });
  await request.post("/api/organize?workflow=" + entry.id, {
    headers,
    data: { action: "move", folder: "Navigation/Nested" },
  });
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Open folder “Navigation”", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "/private/tmp/workbench-workspace-default-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "/private/tmp/workbench-workspace-default-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByRole("button", { name: "Open folder “Navigation”", exact: true })
    .click();
  await expect(page).toHaveURL(/\/folders\/Navigation$/);
  await page
    .getByRole("button", { name: "Open folder “Nested”", exact: true })
    .click();
  expect(readRoute(page.url()).folder).toBe("Navigation/Nested");
  await page.reload();
  await expect(
    page.locator(".workflow-tile").filter({ hasText: "Navigation example" }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("button", { name: "Open folder “Nested”", exact: true }),
  ).toBeVisible();
  await page.goForward();
  await expect(
    page.locator(".workflow-tile").filter({ hasText: "Navigation example" }),
  ).toBeVisible();
  await page
    .getByLabel("Find a workflow", { exact: true })
    .fill("Navigation example");
  expect(new URL(page.url()).searchParams.get("q")).toBe("Navigation example");
  await page
    .getByRole("button", { name: "Open workflow", exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp("/workflows/" + entry.id));
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator('[data-card-id="compute"]').click();
  const link = page.url();
  expect(readRoute(link).view).toBe("edit");
  expect(readRoute(link).display).toBe("list");
  expect(readRoute(link).card).toBe("compute");
  await page.reload();
  await expect(page.getByLabel("Card name", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Workflow settings", exact: true })
    .click();
  expect(readRoute(page.url()).panel).toBe("settings");
  await page.goBack();
  expect(!!readRoute(page.url()).panel).toBeFalsy();
  await page.getByRole("button", { name: "Home", exact: true }).click();
  expect(readRoute(page.url()).folder).toBe("Navigation/Nested");
});

test("browser Back protects unsaved edits and can continue after confirmation", async ({
  page,
  request,
}) => {
  const { entry } = await fixture(page, request, "navigation-draft.yaml");
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await page
    .locator(".workflow-tile")
    .filter({ hasText: "Navigation example" })
    .getByRole("button", { name: "Open workflow", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator('[data-card-id="compute"]').click();
  await page
    .getByLabel("Card name", { exact: true })
    .fill("Unsaved navigation change");
  await page.goBack(); // List -> Flowchart, same workflow draft.
  await expect(
    page.getByRole("button", { name: "Flowchart", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.goBack(); // Edit -> Run, still the same draft.
  await expect(
    page.getByRole("button", { name: "Run", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.evaluate(() => history.back()); // Crossing the Home boundary needs confirmation.
  await expect(
    page.getByRole("dialog", { name: "Leave unsaved changes?" }),
  ).toBeVisible();
  await expect(page).toHaveURL(new RegExp("/workflows/" + entry.id));
  await page.getByRole("button", { name: "Keep editing", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Home", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => history.back());
  await expect(
    page.getByRole("dialog", { name: "Leave unsaved changes?" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Discard draft and continue", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your workflows", exact: true }),
  ).toBeVisible();
  expect(!!readRoute(page.url()).workflow).toBeFalsy();
});

test("function graphs and missing folder locations open directly", async ({
  page,
  request,
}) => {
  const { entry, headers } = await fixture(
    page,
    request,
    "navigation-functions.yaml",
  );
  const record = await (
    await request.get("/api/config?workflow=" + entry.id)
  ).json();
  record.workflow.functions = {
    check: {
      name: "Check readiness",
      graph: "check-graph",
      inputs: {},
      returns: "boolean",
    },
  };
  record.workflow.graphs["check-graph"] = {
    cards: [
      { id: "start", kind: "start", name: "Start" },
      {
        id: "result",
        kind: "return",
        name: "Return readiness",
        config: { returns: "boolean", value: true },
      },
    ],
    edges: [
      {
        id: "start-result",
        kind: "flow",
        source: "start",
        target: "result",
        source_port: "next",
        target_port: "entry",
      },
    ],
  };
  const saved = await request.post("/api/save?workflow=" + entry.id, {
    headers,
    data: { workflow: record.workflow, revision: record.revision },
  });
  expect(saved.ok()).toBeTruthy();
  await page.goto(
    "/workflows/" + entry.id + "/edit/list/functions/check-graph/cards/result",
  );
  await expect(page.getByLabel("Card name", { exact: true })).toHaveValue(
    "Return readiness",
  );
  await expect(
    page.getByText(/Check readiness · returns boolean/),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Card name", { exact: true })).toHaveValue(
    "Return readiness",
  );
  await page.goto("/folders/not-a-real-library-folder");
  await expect(
    page.getByRole("heading", { name: "Folder not found", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Go to My workspace", exact: true })
    .click();
  await expect(
    page
      .getByRole("navigation", { name: "Workflow folders" })
      .getByRole("button", { name: "My workspace", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});
