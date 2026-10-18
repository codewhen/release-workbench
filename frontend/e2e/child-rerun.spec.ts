import { test, expect } from "@playwright/test";

test("stopped child workspace can start a fresh run from here", async ({
  page,
  request,
  context,
}) => {
  await page.goto("/workspace");
  const token = await page
    .locator('meta[name="workbench-token"]')
    .getAttribute("content");
  const headers = { "X-Workbench-Token": token! };
  const flow = (source: string, target: string) => ({
    id: source + target,
    source,
    target,
    source_port: "next",
    target_port: "entry",
    kind: "flow",
  });
  async function save(filename: string, cards: unknown[], edges: unknown[]) {
    const entry = await (
      await request.post("/api/create", {
        headers,
        data: { filename, name: filename },
      })
    ).json();
    const record = await (
      await request.get("/api/config?workflow=" + entry.id)
    ).json();
    record.workflow.graphs.main = { cards, edges };
    record.workflow.layout = {
      main: { positions: { probe: { x: 2500, y: 1400 } } },
    };
    const response = await request.post("/api/save?workflow=" + entry.id, {
      headers,
      data: { workflow: record.workflow, revision: record.revision },
    });
    expect(response.ok()).toBeTruthy();
    return { id: entry.id, ...(await response.json()) };
  }
  const child = await save(
    "rerun-child.yaml",
    [
      { id: "start", kind: "start", name: "Start" },
      {
        id: "probe",
        kind: "python",
        name: "Probe",
        config: {
          code: 'print("fresh selected marker")\nreturn 7',
          returns: "number",
        },
      },
      { id: "wait", kind: "wait", name: "Hold child", config: { seconds: 60 } },
      { id: "finish", kind: "finish", name: "Finish" },
    ],
    [flow("start", "wait"), flow("wait", "probe"), flow("probe", "finish")],
  );
  const parent = await save(
    "rerun-parent.yaml",
    [
      { id: "start", kind: "start", name: "Start" },
      {
        id: "call",
        kind: "workspace",
        name: "Run child",
        config: { path: "rerun-child.yaml", inputs: {} },
      },
      { id: "finish", kind: "finish", name: "Finish" },
    ],
    [flow("start", "call"), flow("call", "finish")],
  );
  await page.goto("/workflows/" + parent.id + "/run/list/cards/call");
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await expect
    .poll(async () => {
      const state = await (
        await request.get("/api/state?workflow=" + parent.id)
      ).json();
      return state.executions["root/main/call"]?.child_active;
    })
    .toContain("Hold child");
  await page.locator('.card-list [data-card-id="call"]').click();
  const opened = context.waitForEvent("page");
  await page
    .locator("aside")
    .getByRole("button", { name: "Open child workflow", exact: true })
    .click();
  const childPage = await opened;
  await expect(childPage).toHaveURL(/\?run=/);
  const original = new URL(childPage.url()).searchParams.get("run")!;
  await expect(
    childPage.getByRole("button", { name: "Run from here", exact: true }),
  ).toBeDisabled();
  await childPage
    .getByRole("button", { name: "Stop all", exact: true })
    .click();
  await expect(childPage.locator(".toolbar .status.cancelled")).toBeVisible();
  await childPage.getByRole("button", { name: "List", exact: true }).click();
  await childPage.getByRole("button", { name: /^Probe Python/ }).click();
  const selected = childPage.getByRole("button", {
    name: "Run from here",
    exact: true,
  });
  await expect(selected).toBeEnabled();
  await childPage
    .getByRole("button", { name: "Flowchart", exact: true })
    .click();
  await selected.click();
  await expect
    .poll(() => new URL(childPage.url()).searchParams.get("run"))
    .not.toBe(original);
  await expect(childPage.locator(".toolbar .status.passed")).toBeVisible();
  await expect(childPage.getByLabel("Probe live output")).toContainText(
    "fresh selected marker",
  );
  await expect(childPage.locator("aside")).toContainText("7");
  await expect
    .poll(async () => {
      const node = await childPage
        .locator('.react-flow__node[data-id="probe"]')
        .boundingBox();
      const canvas = await childPage.locator(".react-flow").boundingBox();
      return node && canvas
        ? Math.max(
            Math.abs(node.x + node.width / 2 - canvas.x - canvas.width / 2),
            Math.abs(node.y + node.height / 2 - canvas.y - canvas.height / 2),
          )
        : 9999;
    })
    .toBeLessThan(25);
  const current = new URL(childPage.url()).searchParams.get("run")!;
  const state = await (
    await request.get(`/api/state?workflow=${child.id}&run=${current}`)
  ).json();
  expect(Object.keys(state.executions)).toEqual([
    "root/main/probe",
    "root/main/finish",
  ]);
  const old = await (
    await request.get(`/api/state?workflow=${child.id}&run=${original}`)
  ).json();
  expect(old.status).toBe("cancelled");
  expect(Object.keys(old.executions)).toContain("root/main/wait");
  await childPage.screenshot({
    path: "/private/tmp/workbench-stopped-child-rerun.png",
  });
  await childPage.close();
});
