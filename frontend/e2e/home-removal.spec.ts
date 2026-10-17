import { test, expect } from "@playwright/test";

test("remove workflows and projects from Home, cancel and restore without deleting files", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New workflow", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Removal example");
  await page
    .getByLabel("Filename", { exact: true })
    .fill("removal-example.yaml");
  await expect(
    page.getByLabel("Project folder", { exact: true }),
  ).not.toHaveValue("");
  const project = await page
    .getByLabel("Project folder", { exact: true })
    .inputValue();
  await page
    .getByRole("button", { name: "Create workflow", exact: true })
    .click();
  await page.getByRole("button", { name: "Home", exact: true }).click();
  const row = page.locator(".workflow-row").filter({
    has: page.getByRole("heading", { name: "Removal example", exact: true }),
  });
  await expect(
    row.getByRole("button", { name: "Remove from Home", exact: true }),
  ).toHaveCount(0);
  await row.click({ button: "right" });
  await page.getByRole("menuitem", { name: "Remove from Home" }).click();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(row).toBeVisible();
  await row.click({ button: "right" });
  await page.getByRole("menuitem", { name: "Remove from Home" }).click();
  await expect(page.getByRole("dialog")).toContainText("Files on disk");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Remove from Home", exact: true })
    .click();
  await expect(row).toHaveCount(0);
  await page.reload();
  await expect(row).toHaveCount(0);
  await page
    .getByRole("button", { name: "Add project or file", exact: true })
    .click();
  await page.getByLabel("Absolute folder or YAML path").fill(project);
  await page
    .getByRole("button", { name: "Add to library", exact: true })
    .click();
  await expect(row).toBeVisible();
  await page.getByRole("combobox", { name: "Project", exact: true }).click();
  await page.getByRole("option", { name: project, exact: true }).click();
  await page
    .getByRole("button", { name: "Remove project from Home", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Remove from Home", exact: true })
    .click();
  await expect(row).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "New workflow", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "/private/tmp/workbench-home-removal-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "/private/tmp/workbench-home-removal-desktop.png",
    fullPage: true,
  });
});
