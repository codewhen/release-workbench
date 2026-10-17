import { test, expect } from "@playwright/test";

test("long result sources stay inside cards without clipping their ports", async ({
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
      data: { filename: "card-overflow.yaml", name: "Card sizing example" },
    })
  ).json();
  const record = await (
    await request.get("/api/config?workflow=" + entry.id)
  ).json();
  const sourceName =
    "Collect background checks results with an exceptionally long descriptive name";
  record.workflow.graphs.main = {
    cards: [
      { id: "start", kind: "start", name: "Start" },
      {
        id: "collect",
        kind: "python",
        name: sourceName,
        config: { code: "return {}", returns: "object" },
      },
      {
        id: "finish",
        kind: "finish",
        name: "Finish",
        config: { returns: "object", value: { $ref: "card:collect" } },
      },
    ],
    edges: [
      ["start", "collect"],
      ["collect", "finish"],
    ].map(([source, target]) => ({
      id: source + target,
      kind: "flow",
      source,
      target,
      source_port: "next",
      target_port: "entry",
    })),
  };
  record.workflow.layout = {
    main: {
      positions: {
        start: { x: 0, y: 0 },
        collect: { x: 340, y: 0 },
        finish: { x: 680, y: 0 },
      },
      areas: [],
    },
  };
  const saved = await request.post("/api/save?workflow=" + entry.id, {
    headers,
    data: { workflow: record.workflow, revision: record.revision },
  });
  expect(saved.ok()).toBeTruthy();
  await page.goto("/?workflow=" + entry.id);
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("button", { name: "Flowchart", exact: true }).click();
  const finish = page.locator('.react-flow__node[data-id="finish"]');
  const source = finish.getByRole("combobox", {
    name: "Result source",
    exact: true,
  });
  await expect(source).toContainText(sourceName);
  for (const viewport of [
    { width: 1440, height: 1000 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.getByRole("button", { name: "Flowchart", exact: true }).click();
    await page
      .getByRole("button", { name: "Fit workflow", exact: true })
      .click();
    await expect(source).toBeVisible();
    const overflow = await page.locator(".flow-card").evaluateAll((cards) =>
      cards.flatMap((card) => {
        const bounds = card.getBoundingClientRect();
        return [
          ...card.querySelectorAll(
            "label, .choice, .choice-trigger, .terminal-result, .terminal-result small, input, textarea",
          ),
        ]
          .filter((field) => {
            const box = field.getBoundingClientRect();
            return (
              box.width > 0 &&
              (box.right > bounds.right + 1 || box.left < bounds.left - 1)
            );
          })
          .map((field) => field.className || field.tagName);
      }),
    );
    expect(overflow).toEqual([]);
    await page.screenshot({
      path: `/private/tmp/workbench-card-sizing-${viewport.width}.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Flowchart", exact: true }).click();
  await page.getByRole("button", { name: "Fit workflow", exact: true }).click();
  await source.click();
  await expect(
    page.getByRole("option", {
      name: "Result of “" + sourceName + "”",
      exact: true,
    }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(finish.locator('[aria-label="Entry for Finish"]')).toBeVisible();
});
