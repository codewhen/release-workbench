import { test, expect } from "@playwright/test";

test("project discovery, runtime Python, manual evidence and report links", async ({
  page,
}) => {
  await page.goto("/");
  const id = await page.evaluate(async () => {
    const token = document.querySelector<HTMLMetaElement>(
      'meta[name="workbench-token"]',
    )!.content;
    const library = await (await fetch("/api/library")).json();
    const detection = {
      serial: [{ value: "SYNTHETIC_ONE", label: "Synthetic phone" }],
      warnings: ["Synthetic discovery fixture"],
    };
    const raw = {
      version: 3,
      name: "Project workflow fixture",
      workspace: ".",
      inputs: { serial: { type: "string", default: "" } },
      input_detection: {
        argv: [
          { $ref: "runtime:python" },
          "-c",
          "print(" + JSON.stringify(JSON.stringify(detection)) + ")",
        ],
      },
      report_paths: ["reports/**/*.json"],
      graphs: {
        main: {
          cards: [
            { id: "start", kind: "start", name: "Start" },
            {
              id: "command",
              kind: "program",
              name: "Write fixture report",
              config: {
                argv: [
                  { $ref: "runtime:python" },
                  "-c",
                  'from pathlib import Path; import json; p=Path("reports/result.json"); p.parent.mkdir(exist_ok=True); p.write_text("{\\"passed\\":true}"); print(json.dumps({"passed":True}))',
                ],
                capture: "json",
              },
            },
            {
              id: "approve",
              kind: "manual",
              name: "Review fixture",
              config: {
                mode: "approval",
                instructions: "Verify the synthetic report.",
              },
            },
            {
              id: "finish",
              kind: "finish",
              name: "Finish",
              config: { returns: "object", value: { $ref: "card:command" } },
            },
          ],
          edges: [
            ["start", "command"],
            ["command", "approve"],
            ["approve", "finish"],
          ].map(([source, target]) => ({
            id: source + target,
            source,
            target,
            source_port: "next",
            target_port: "entry",
            kind: "flow",
          })),
        },
      },
    };
    const response = await fetch("/api/import", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Workbench-Token": token,
      },
      body: JSON.stringify({
        project: library.projects[0],
        filename: "project-fixture.yaml",
        yaml: JSON.stringify(raw),
      }),
    });
    if (!response.ok) throw Error(await response.text());
    return (await response.json()).id;
  });
  await page.goto("/?workflow=" + id);
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await page
    .getByRole("button", { name: "Auto-detect inputs", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "Synthetic discovery fixture",
  );
  await expect(page.getByLabel("serial", { exact: true })).toHaveValue(
    "SYNTHETIC_ONE",
  );
  await page.screenshot({ path: "/private/tmp/workbench-input-discovery.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "/private/tmp/workbench-input-discovery-mobile.png",
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Run workflow", exact: true }).click();
  await page
    .getByLabel("Evidence notes", { exact: true })
    .fill("Verified synthetic fixture report");
  await page
    .getByRole("button", { name: "Return result and continue", exact: true })
    .click();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  await page.getByText("Report files (1)", { exact: true }).click();
  const link = page.getByRole("link", {
    name: "reports/result.json",
    exact: true,
  });
  await expect(link).toBeVisible();
  const response = await page.request.get((await link.getAttribute("href"))!);
  expect(await response.json()).toEqual({ passed: true });
  const escape = await page.request.get(
    "/api/attachment?workflow=" + id + "&path=../secret",
  );
  expect(escape.status()).toBe(404);
});

test("child workflows expose their exact live execution in a separate workspace", async ({
  page,
  context,
}) => {
  await page.goto("/");
  const id = await page.evaluate(async () => {
    const token = document.querySelector<HTMLMetaElement>(
      'meta[name="workbench-token"]',
    )!.content;
    const library = await (await fetch("/api/library")).json();
    const flow = (source: string, target: string) => ({
      id: source + target,
      source,
      target,
      source_port: "next",
      target_port: "entry",
      kind: "flow",
    });
    const save = async (filename: string, raw: unknown) => {
      const response = await fetch("/api/import", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Workbench-Token": token,
        },
        body: JSON.stringify({
          project: library.projects[0],
          filename,
          yaml: JSON.stringify(raw),
        }),
      });
      if (!response.ok) throw Error(await response.text());
      return (await response.json()).id;
    };
    await save("child-evidence.yaml", {
      version: 3,
      name: "Synthetic child",
      graphs: {
        main: {
          cards: [
            { id: "start", name: "Start", kind: "start" },
            {
              id: "probe",
              name: "Probe",
              kind: "python",
              config: {
                code: 'import time\nprint("forwarded child marker", flush=True)\nprint(\'::workbench::{"done":1,"total":2,"stage":"child probe"}\', flush=True)\ntime.sleep(2)\nreturn 42',
                returns: "number",
              },
            },
            {
              id: "review",
              name: "Review child",
              kind: "manual",
              config: {
                mode: "approval",
                instructions: "Confirm synthetic child evidence.",
              },
            },
            {
              id: "finish",
              name: "Finish",
              kind: "finish",
              config: { returns: "number", value: { $ref: "card:probe" } },
            },
          ],
          edges: [
            flow("start", "probe"),
            flow("probe", "review"),
            flow("review", "finish"),
          ],
        },
      },
    });
    return save("parent-evidence.yaml", {
      version: 3,
      name: "Synthetic parent",
      graphs: {
        main: {
          cards: [
            { id: "start", name: "Start", kind: "start" },
            {
              id: "child",
              name: "Run child",
              kind: "workspace",
              config: { path: "child-evidence.yaml", inputs: {} },
            },
            {
              id: "finish",
              name: "Finish",
              kind: "finish",
              config: { returns: "number", value: { $ref: "card:child" } },
            },
          ],
          edges: [flow("start", "child"), flow("child", "finish")],
        },
      },
    });
  });
  await page.goto("/?workflow=" + id);
  await page.getByRole("button", { name: "Run all", exact: true }).click();
  await page.locator('.react-flow__node[data-id="child"]').click();
  await expect(page.getByLabel("Run child live output")).toContainText(
    "forwarded child marker",
  );
  await expect(page.locator("aside")).toContainText("Child stage: child probe");
  const opened = context.waitForEvent("page");
  await page
    .locator("aside")
    .getByRole("button", { name: "Open child workflow", exact: true })
    .click();
  const childPage = await opened;
  await expect(childPage).toHaveURL(/\/workflows\/[^/]+\/run\?run=/);
  await expect(
    childPage.getByText("Execution view ·", { exact: false }),
  ).toBeVisible();
  await expect(
    childPage.getByRole("button", { name: "Run all", exact: true }),
  ).toBeDisabled();
  await expect(
    childPage.getByRole("button", { name: "Edit", exact: true }),
  ).toBeDisabled();
  await expect(childPage.locator(".toolbar .status.running")).toBeVisible();
  // Reload preserves the exact invocation and its pending manual evidence.
  await childPage.reload();
  await childPage
    .getByLabel("Evidence notes", { exact: true })
    .fill("Confirmed directly from child workspace");
  await childPage.screenshot({
    path: "/private/tmp/workbench-child-live-prompt.png",
  });
  await childPage
    .getByRole("button", { name: "Return result and continue", exact: true })
    .click();
  await expect(childPage.locator(".toolbar .status.passed")).toBeVisible();
  await childPage.locator('.react-flow__node[data-id="probe"]').click();
  await expect(childPage.getByLabel("Probe live output")).toContainText(
    "forwarded child marker",
  );
  await expect(childPage.locator("aside")).toContainText("42");
  await childPage.screenshot({
    path: "/private/tmp/workbench-child-live-result.png",
  });
  for (const name of ["Saved log", "Open complete HTML report"]) {
    const link = childPage.getByRole("link", { name, exact: true });
    expect(
      (
        await childPage.request.get((await link.getAttribute("href"))!)
      ).status(),
    ).toBe(200);
  }
  await childPage.close();
  await expect(page.locator(".toolbar .status.passed")).toBeVisible();
  const report = page.getByRole("link", {
    name: "Open child workflow report",
    exact: true,
  });
  await expect(report).toBeVisible();
  expect(
    (await page.request.get((await report.getAttribute("href"))!)).status(),
  ).toBe(200);
});
