import { test, expect, type Page } from "@playwright/test";
async function open(page: Page, name: string) {
  await page.goto("/");
  await page
    .locator(".workflow-row")
    .filter({ has: page.getByRole("heading", { name, exact: true }) })
    .getByRole("button", { name: "Open workflow" })
    .click();
  await expect(
    page.getByRole("button", { name: "Edit", exact: true }),
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

test("unfinished cards save and reload as a draft while Run stays blocked", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New workflow", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Unfinished draft");
  await page.getByLabel("Filename", { exact: true }).fill("unfinished.yaml");
  await page
    .getByRole("button", { name: "Create workflow", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page
    .getByRole("button", { name: "Add card", exact: true })
    .first()
    .click();
  await page
    .getByRole("menuitem", { name: "Manual decision / approval", exact: true })
    .click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Draft saved");
  await expect(
    page.getByRole("button", { name: /Main workflow › Manual.*next/ }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await expect(page.locator("[data-card-id]")).toHaveCount(3);
  await expect(
    page.getByRole("region", { name: "Workflow validation" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Run not started");
  await expect(
    page.getByRole("region", { name: "Workflow validation" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page
    .getByRole("button", { name: "Validate & review", exact: true })
    .click();
  await expect(
    page.getByRole("region", { name: "Workflow validation" }),
  ).toContainText("no execution connection");
  await expect(
    page.getByRole("dialog", { name: "Action required" }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: /Main workflow › Manual.*next/ })
    .click();
  await expect(page.getByLabel("Card name", { exact: true })).toHaveValue(
    "Manual decision / approval",
  );
});
test("unfinished graph can switch between YAML and flowchart without run validation", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .locator(".workflow-row")
    .filter({
      has: page.getByRole("heading", { name: "Unfinished draft", exact: true }),
    })
    .getByRole("button", { name: "Open workflow" })
    .click();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "Yaml", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Workflow YAML", exact: true }),
  ).toHaveValue(/Manual decision/);
  await page.getByRole("button", { name: "List", exact: true }).click();
  await expect(page.locator("[data-card-id]")).toHaveCount(3);
});

test("old editor validation failure recovers its unsaved draft on reload", async ({
  page,
  request,
}) => {
  await open(page, "Unfinished draft");
  const key = new URL(page.url()).searchParams.get("workflow")!;
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const response = await request.get("/api/config?workflow=" + key);
  const record = await response.json();
  const raw = record.workflow;
  raw.graphs.main.cards.push({
    id: "legacy-unsaved",
    kind: "wait",
    name: "Recovered wait",
    config: { seconds: 1 },
  });
  const rejected = await request.post("/api/validate?workflow=" + key, {
    headers: { "X-Workbench-Token": token! },
    data: { workflow: raw },
  });
  expect(rejected.status()).toBe(400);
  await page.reload();
  await expect(page.getByRole("status")).toContainText(
    "Recovered your unsaved draft",
  );
  await page.getByRole("button", { name: "List", exact: true }).click();
  await expect(page.locator('[data-card-id="legacy-unsaved"]')).toBeVisible();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Draft saved");
  await page.reload();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await expect(page.locator('[data-card-id="legacy-unsaved"]')).toBeVisible();
  await expect(
    page.getByText("Recovered your unsaved draft. Save to keep it.", {
      exact: true,
    }),
  ).toHaveCount(0);
});

test("validation appears only on request and is cleared when fields change", async ({
  page,
  request,
}) => {
  await open(page, "Blank flowchart");
  const key = new URL(page.url()).searchParams.get("workflow")!;
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const record = await (
    await request.get("/api/config?workflow=" + key)
  ).json();
  const finish = record.workflow.graphs.main.cards.find(
    (c: { kind: string }) => c.kind === "finish",
  );
  finish.name = "Publish result";
  finish.config = { returns: "boolean", value: null };
  const response = await request.post("/api/save?workflow=" + key, {
    headers: { "X-Workbench-Token": token! },
    data: { workflow: record.workflow, revision: record.revision },
  });
  expect(response.status()).toBe(200);
  await page.reload();
  const validation = page.getByRole("region", { name: "Workflow validation" });
  await expect(validation).toHaveCount(0);
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(validation).toContainText("1 issue prevents running");
  await validation
    .getByRole("button", { name: /Main workflow › Publish result/ })
    .click();
  await expect(page.getByLabel("Card name", { exact: true })).toHaveValue(
    "Publish result",
  );
  await expect(
    page.getByRole("button", { name: "Flowchart", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".react-flow__node.selected")).toContainText(
    "Publish result",
  );
  await page
    .getByRole("complementary", { name: "Card settings" })
    .getByLabel("Workflow output", { exact: true })
    .fill("false");
  await expect(validation).toHaveCount(0);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(validation).toContainText("Ready to run");
  await expect(page.getByRole("status")).toContainText("Workflow saved.");
});

test("completion markers select Python and Calculate results without extra wires", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const headers = { "X-Workbench-Token": token! };
  const entry = await (
    await request.post("/api/create", {
      headers,
      data: { filename: "terminal-results.yaml", name: "Terminal results" },
    })
  ).json();
  const record = await (
    await request.get("/api/config?workflow=" + entry.id)
  ).json();
  const card = (id: string, kind: string, name: string, config = {}) => ({
    id,
    kind,
    name,
    config,
  });
  const edge = (source: string, target: string) => ({
    id: source + target,
    kind: "flow",
    source,
    target,
    source_port: "next",
    target_port: "entry",
  });
  record.workflow.functions = {
    check: { graph: "check", returns: "boolean", inputs: {} },
  };
  record.workflow.graphs = {
    main: {
      cards: [
        card("start", "start", "Start"),
        card("call", "call", "Call check", { function: "check" }),
        card("calculate", "calculate", "Calculate", {
          operation: "add",
          left: 2,
          right: 3,
        }),
        card("finish", "finish", "Finish"),
      ],
      edges: [
        edge("start", "call"),
        edge("call", "calculate"),
        edge("calculate", "finish"),
      ],
    },
    check: {
      cards: [
        card("start", "start", "Start"),
        card("python", "python", "Python", {
          code: "return False",
          returns: "boolean",
        }),
        card("wrong", "finish", "Finish"),
      ],
      edges: [edge("start", "python"), edge("python", "wrong")],
    },
  };
  expect(
    (
      await request.post("/api/save?workflow=" + entry.id, {
        headers,
        data: { workflow: record.workflow, revision: record.revision },
      })
    ).status(),
  ).toBe(200);
  await page.goto("/?workflow=" + entry.id);
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page
    .getByRole("button", { name: "Validate & review", exact: true })
    .click();
  await page
    .getByRole("region", { name: "Workflow validation" })
    .getByRole("button", { name: /Function “check” › Finish/ })
    .click();
  await expect(
    page.getByRole("button", { name: "Flowchart", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".react-flow__node.selected")).toContainText(
    "Finish",
  );
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page
    .getByRole("button", { name: "Replace with Return", exact: true })
    .click();
  await choose(page, "Result source", "Result of “Python”");
  await page
    .getByRole("button", { name: "Back to caller", exact: true })
    .click();
  await page.locator('[data-card-id="finish"]').click();
  await choose(page, "Result source", "Result of “Calculate”");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Workflow validation" }),
  ).toContainText("Ready to run");
  await choose(page, "Result source", "No result (Void)");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Workflow validation" }),
  ).toContainText("Ready to run");
  await choose(page, "Result source", "Result of “Calculate”");
  await page.getByRole("button", { name: "Save and run", exact: true }).click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  const state = await (
    await request.get("/api/state?workflow=" + entry.id)
  ).json();
  const executions = Object.values(state.executions) as {
    card: string;
    outcome: { value: { value: unknown } };
  }[];
  expect(executions.find((c) => c.card === "finish")?.outcome.value.value).toBe(
    5,
  );
  expect(executions.find((c) => c.card === "call")?.outcome.value.value).toBe(
    false,
  );
});

test("selected run card keeps live logs, trail and returned value visible", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const headers = { "X-Workbench-Token": token! };
  const entry = await (
    await request.post("/api/create", {
      headers,
      data: { filename: "live-details.yaml", name: "Live card details" },
    })
  ).json();
  const record = await (
    await request.get("/api/config?workflow=" + entry.id)
  ).json();
  record.workflow.graphs.main.cards.splice(1, 0, {
    id: "python",
    kind: "python",
    name: "Python probe",
    config: {
      returns: "boolean",
      code: "import time\nprint('probe started', flush=True)\ntime.sleep(3)\nprint('probe completed', flush=True)\nreturn False",
    },
  });
  record.workflow.graphs.main.edges = [
    {
      id: "start-python",
      source: "start",
      target: "python",
      source_port: "next",
      target_port: "entry",
      kind: "flow",
    },
    {
      id: "python-finish",
      source: "python",
      target: "finish",
      source_port: "next",
      target_port: "entry",
      kind: "flow",
    },
  ];
  expect(
    (
      await request.post("/api/save?workflow=" + entry.id, {
        headers,
        data: { workflow: record.workflow, revision: record.revision },
      })
    ).status(),
  ).toBe(200);
  await page.goto("/?workflow=" + entry.id);
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await page.locator('[data-card-id="python"]').click();
  const panel = page.getByRole("complementary", { name: "Card execution" });
  await expect(
    panel.getByLabel("Python probe live output", { exact: true }),
  ).toContainText("probe started");
  await expect(
    panel.getByRole("region", { name: "Python probe live trail" }),
  ).toContainText("started");
  await expect(
    panel.getByLabel("Python probe returned value", { exact: true }),
  ).toHaveText("false");
  await expect(
    panel.getByLabel("Python probe live output", { exact: true }),
  ).toContainText("probe completed");
  await expect(
    panel.getByRole("region", { name: "Python probe live trail" }),
  ).toContainText("finished · passed");
  await panel.getByRole("button", { name: "Overall run", exact: true }).click();
  await expect(
    page.getByRole("complementary", { name: "Overall run" }),
  ).toBeVisible();
});

test("Compare chooses Get Count by name instead of requiring reference JSON", async ({
  page,
  request,
}) => {
  await open(page, "While with a Boolean function");
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator('[data-card-id="repeat"]').click();
  await page
    .getByRole("button", { name: "Open function", exact: true })
    .click();
  await page.locator('[data-card-id="compare"]').click();
  await expect(
    page.getByRole("combobox", { name: "First value source", exact: true }),
  ).toContainText("Result of “Get Count”");
  await expect(
    page.getByRole("textbox", { name: "First value", exact: true }),
  ).toHaveCount(0);
  await choose(page, "First value source", "Type a value");
  await page.getByLabel("First value", { exact: true }).fill("0");
  await choose(page, "First value source", "Result of “Get Count”");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(
    page.getByRole("region", { name: "Workflow validation" }),
  ).toContainText("Ready to run");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("saved");
  const key = new URL(page.url()).searchParams.get("workflow")!;
  const record = await (
    await request.get("/api/config?workflow=" + key)
  ).json();
  expect(
    record.workflow.graphs.condition.cards.find(
      (c: { id: string }) => c.id === "compare",
    ).config.left,
  ).toEqual({ $ref: "card:get-count" });
  await page
    .getByRole("button", { name: "Back to caller", exact: true })
    .click();
  await page.getByRole("button", { name: "Run", exact: true }).click();
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  const state = await (await request.get("/api/state?workflow=" + key)).json();
  expect(state.globals.count).toBe(3);
});

test("Variable card opens global declaration and initialization settings", async ({
  page,
  request,
}) => {
  await open(page, "While with a Boolean function");
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.locator('[data-card-id="increment"]').click();
  await page
    .getByRole("button", { name: "Create / initialize global", exact: true })
    .click();
  await expect(
    page.getByLabel("New global variable name", { exact: true }),
  ).toBeFocused();
  await page
    .getByLabel("New global variable name", { exact: true })
    .fill("attempts");
  await page
    .getByRole("button", { name: "Add global variable", exact: true })
    .click();
  await choose(page, "attempts type", "number");
  const variable = page
    .locator(".declaration")
    .filter({ has: page.getByText("attempts", { exact: true }) });
  await variable.getByLabel("Initial value", { exact: true }).fill("0");
  await expect(
    page.getByRole("region", { name: "Workflow validation" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("saved");
  const key = new URL(page.url()).searchParams.get("workflow")!;
  const record = await (
    await request.get("/api/config?workflow=" + key)
  ).json();
  expect(record.workflow.globals.attempts).toEqual({
    type: "number",
    initial: 0,
  });
});

test("context menu fits near the bottom and remains contained after resize", async ({
  page,
}) => {
  await open(page, "While with a Boolean function");
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "Flowchart", exact: true }).click();
  const pane = page.locator(".react-flow__pane");
  const bounds = await pane.boundingBox();
  await pane.click({
    button: "right",
    position: { x: bounds!.width / 2, y: bounds!.height - 5 },
  });
  const menu = page.getByRole("menu", { name: "Add a card", exact: true });
  await expect(menu).toBeVisible();
  for (const size of [
    { width: 1440, height: 1000 },
    { width: 600, height: 400 },
    { width: 390, height: 320 },
  ]) {
    await page.setViewportSize(size);
    await expect
      .poll(async () => {
        const box = await menu.boundingBox();
        return (
          !!box &&
          box.x >= 11 &&
          box.y >= 11 &&
          box.x + box.width <= size.width - 11 &&
          box.y + box.height <= size.height - 11
        );
      })
      .toBe(true);
    await menu.press("End");
    await expect(menu.getByRole("menuitem").last()).toBeInViewport();
  }
  await menu.press("Escape");
  await expect(menu).toHaveCount(0);
});

test("Home chooses a project folder and preserves the path on cancel", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Add project or file" }).click();
  let selected: string | null = "/tmp/example-project";
  await page.route("**/api/pick-folder", async (route) => {
    await route.fulfill({ json: { path: selected } });
  });
  await page.getByRole("button", { name: "Choose project folder…" }).click();
  await expect(page.getByLabel("Absolute folder or YAML path")).toHaveValue(
    selected,
  );
  selected = null;
  await page.getByRole("button", { name: "Choose project folder…" }).click();
  await expect(
    page.getByRole("button", { name: "Choose project folder…" }),
  ).toBeEnabled();
  await expect(page.getByLabel("Absolute folder or YAML path")).toHaveValue(
    "/tmp/example-project",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Choose project folder…" }),
  ).toBeInViewport();
});
