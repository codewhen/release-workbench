import { test, expect, type Page } from "@playwright/test";

async function addFolder(page: Page, name: string) {
  await page.getByRole("button", { name: "New folder", exact: true }).click();
  await page.getByLabel("Folder name", { exact: true }).fill(name);
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Save", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
}
const tile = (page: Page, name: string) =>
  page.getByRole("button", { name: `Open folder “${name}”`, exact: true });

test("nested folders, grid navigation, subtree rename/move and workflow placement", async ({
  page,
}) => {
  await page.goto("/");
  await addFolder(page, "Tests");
  await addFolder(page, "Archive");
  await tile(page, "Tests").click();
  await addFolder(page, "Phone");
  await tile(page, "Phone").click();
  await addFolder(page, "Recovery");
  await tile(page, "Recovery").click();
  await expect(
    page.getByRole("navigation", { name: "Folder breadcrumbs" }),
  ).toContainText("Phone");
  await page.getByRole("button", { name: "New workflow", exact: true }).click();
  await page.getByLabel("Name", { exact: true }).fill("Nested workflow");
  await page
    .getByLabel("Filename", { exact: true })
    .fill("nested-workflow.yaml");
  await page
    .getByRole("button", { name: "Create workflow", exact: true })
    .click();
  await page.getByRole("button", { name: "Home", exact: true }).click();
  const library = () =>
    page.evaluate(async () => (await fetch("/api/library")).json());
  expect(
    (await library()).entries.find(
      (entry: { name: string }) => entry.name === "Nested workflow",
    ).folder,
  ).toBe("Tests/Phone/Recovery");
  await page
    .getByRole("navigation", { name: "Folder breadcrumbs" })
    .getByRole("button", { name: "My workspace", exact: true })
    .click();
  await tile(page, "Tests").click();
  await tile(page, "Phone").focus();
  await page.keyboard.press("Shift+F10");
  await page
    .getByRole("menuitem", { name: "Rename folder", exact: true })
    .click();
  await page.getByLabel("Folder name", { exact: true }).fill("Devices");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Save", exact: true })
    .click();
  await expect(tile(page, "Devices")).toBeVisible();
  await tile(page, "Devices").click({ button: "right" });
  await page
    .getByRole("menuitem", { name: "Move folder", exact: true })
    .click();
  await page
    .getByRole("combobox", { name: "Move to folder", exact: true })
    .click();
  await expect(
    page.getByRole("option", { name: "Tests/Devices/Recovery", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("option", { name: "Archive", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Save", exact: true })
    .click();
  expect(
    (await library()).entries.find(
      (entry: { name: string }) => entry.name === "Nested workflow",
    ).folder,
  ).toBe("Archive/Devices/Recovery");
  await page
    .getByRole("navigation", { name: "Workflow folders" })
    .getByRole("button", { name: "Archive", exact: true })
    .click();
  await tile(page, "Devices").click();
  await tile(page, "Recovery").click();
  await expect(
    page.locator(".workflow-tile").filter({ hasText: "Nested workflow" }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Folder breadcrumbs" })
    .getByRole("button", { name: "Archive", exact: true })
    .click();
  await tile(page, "Devices").click({ button: "right" });
  await page.getByRole("menuitem", { name: /^Remove folder/ }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancel", exact: true })
    .click();
  await expect(tile(page, "Devices")).toBeVisible();
  await tile(page, "Devices").click({ button: "right" });
  await page.getByRole("menuitem", { name: /^Remove folder/ }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Save", exact: true })
    .click();
  await expect(
    page.locator(".workflow-tile").filter({ hasText: "Nested workflow" }),
  ).toBeVisible();
  await page.reload();
  expect(
    (await library()).entries.find(
      (entry: { name: string }) => entry.name === "Nested workflow",
    ).folder,
  ).toBe("Archive");
  await page
    .getByRole("navigation", { name: "Workflow folders" })
    .getByRole("button", { name: "All workflows", exact: true })
    .click();
  await page.screenshot({
    path: "/private/tmp/workbench-folder-grid-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "/private/tmp/workbench-folder-grid-mobile.png",
    fullPage: true,
  });
});
