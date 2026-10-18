import { test, expect } from "@playwright/test";

test("Run from here executes the remaining flow and keeps its result visible", async ({
  page,
  request,
}) => {
  await page.goto("/workspace");
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const headers = { "X-Workbench-Token": token! };
  const entry = await (
    await request.post("/api/create", {
      headers,
      data: { filename: "selected-only.yaml", name: "Selected-card example" },
    })
  ).json();
  const record = await (
    await request.get("/api/config?workflow=" + entry.id)
  ).json();
  record.workflow.graphs.main = {
    cards: [
      { id: "start", kind: "start", name: "Start" },
      {
        id: "before",
        kind: "python",
        name: "Must not run before",
        config: { code: 'raise Exception("before ran")' },
      },
      {
        id: "selected",
        kind: "python",
        name: "Compute sample",
        config: {
          code: 'print("selected-only log")\nreturn 17',
          returns: "number",
        },
      },
      {
        id: "after",
        kind: "python",
        name: "Must not run after",
        config: { code: 'print("after marker")\nreturn 21' },
      },
      { id: "finish", kind: "finish", name: "Finish" },
    ],
    edges: [
      ["start", "before"],
      ["before", "selected"],
      ["selected", "after"],
      ["after", "finish"],
    ].map(([source, target]) => ({
      id: source + target,
      source,
      target,
      source_port: "next",
      target_port: "entry",
      kind: "flow",
    })),
  };
  record.workflow.layout = {
    main: { positions: { selected: { x: 3600, y: 1800 } } },
  };
  expect(
    (
      await request.post("/api/save?workflow=" + entry.id, {
        headers,
        data: { workflow: record.workflow, revision: record.revision },
      })
    ).ok(),
  ).toBeTruthy();
  await page.goto("/workflows/" + entry.id + "/run/list");
  const runSelected = page.getByRole("button", {
    name: "Run from here",
    exact: true,
  });
  await expect(runSelected).toBeDisabled();
  await page.getByRole("button", { name: /Compute sample/ }).click();
  await expect(runSelected).toBeEnabled();
  await runSelected.click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  await expect(page.getByLabel("Compute sample live output")).toContainText(
    "selected-only log",
  );
  await expect(page.locator("aside")).toContainText("17");
  const state = await (
    await request.get("/api/state?workflow=" + entry.id)
  ).json();
  expect(Object.keys(state.executions)).toEqual([
    "root/main/selected",
    "root/main/after",
    "root/main/finish",
  ]);
  expect(state.selection.card).toBe("selected");
  await page.getByRole("button", { name: "Flowchart", exact: true }).click();
  await runSelected.click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  await expect
    .poll(async () => {
      const box = await page
        .locator('.react-flow__node[data-id="selected"]')
        .boundingBox();
      const canvas = await page.locator(".react-flow").boundingBox();
      if (!box || !canvas) return 9999;
      return Math.max(
        Math.abs(box.x + box.width / 2 - canvas.x - canvas.width / 2),
        Math.abs(box.y + box.height / 2 - canvas.y - canvas.height / 2),
      );
    })
    .toBeLessThan(25);
  const selectedBox = await page
    .locator('.react-flow__node[data-id="selected"]')
    .boundingBox();
  expect(selectedBox!.width).toBeGreaterThan(200);
  await page.screenshot({ path: "/private/tmp/workbench-selected-focus.png" });
  await page.getByRole("button", { name: "List", exact: true }).click();
  await page.screenshot({
    path: "/private/tmp/workbench-run-selected-desktop.png",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(runSelected).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "/private/tmp/workbench-run-selected-mobile.png",
  });
  // A selected-card result cannot be resumed into a full workflow approval.
  await expect
    .poll(
      async () =>
        (await (await request.get("/api/state?workflow=" + entry.id)).json())
          .busy,
    )
    .toBe(false);
  const resume = await request.post("/api/run?workflow=" + entry.id, {
    headers,
    data: {
      revision: (
        await (await request.get("/api/config?workflow=" + entry.id)).json()
      ).revision,
      resume: state.run_id,
    },
  });
  expect(resume.ok()).toBeFalsy();
  expect((await resume.json()).error).toContain("changed");
});

test("Run from here at Join collects completed parallel outputs and proceeds to Finish", async ({
  page,
  request,
}) => {
  await page.goto("/workspace");
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const headers = { "X-Workbench-Token": token! };
  const entry = await (
    await request.post("/api/create", {
      headers,
      data: {
        filename: "join-from-here.yaml",
        name: "Collect race results example",
        template: "parallel",
      },
    })
  ).json();
  const record = await (
    await request.get("/api/config?workflow=" + entry.id)
  ).json();
  const graph = record.workflow.graphs.main;
  graph.cards.find((c: { id: string }) => c.id === "join").name =
    "Collect race results";
  graph.cards.find((c: { id: string }) => c.id === "finish").config = {
    returns: "object",
    value: { $ref: "card:join" },
  };
  expect(
    (
      await request.post("/api/save?workflow=" + entry.id, {
        headers,
        data: { workflow: record.workflow, revision: record.revision },
      })
    ).ok(),
  ).toBeTruthy();
  await page.goto("/workflows/" + entry.id + "/run/list");
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run all", exact: true }),
  ).toBeEnabled();
  await page.locator('.card-list [data-card-id="join"]').click();
  await page
    .getByRole("button", { name: "Run from here", exact: true })
    .click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  await expect(page.locator("aside")).toContainText("Reused earlier results");
  const state = await (
    await request.get("/api/state?workflow=" + entry.id)
  ).json();
  expect(Object.keys(state.executions)).toEqual([
    "root/main/join",
    "root/main/finish",
  ]);
  expect(state.result.value.first.value).toBe("first completed");
  expect(state.result.value.second.value).toBe("second completed");
  await page.screenshot({
    path: "/private/tmp/workbench-run-from-here-join.png",
  });
});
