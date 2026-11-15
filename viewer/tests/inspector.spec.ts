import { test, expect } from "@playwright/test";

test("search, exact evidence, references, and recorded actions", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Knowledge inspector" }),
  ).toBeVisible();
  await expect(
    page.getByText("Connected to local index", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search knowledge" })
    .fill("refresh tokens expire");
  await page.getByRole("button", { name: "Run search", exact: true }).click();
  const hit = page
    .locator(".result-row")
    .filter({ hasText: "Refresh tokens expire after 30 days" })
    .first();
  await expect(hit).toBeVisible();
  await hit.click();
  await expect(page.locator(".evidence pre")).toContainText(
    "Refresh tokens expire after 30 days.",
  );
  await expect(page.locator(".related")).toContainText("Revocation");
  await page.locator(".related").click();
  await expect(page.locator(".inspector .selected-info h3")).toHaveText(
    "Revocation",
  );
  await page
    .getByRole("button", { name: "Retrieval traces", exact: true })
    .click();
  await expect(page.locator(".run-row").first()).toBeVisible();
  await page.locator(".run-row").first().click();
  await expect(page.locator(".trace-player")).toBeVisible();
  await page.getByRole("button", { name: "Next recorded action" }).click();
  await page.screenshot({
    path: "/tmp/navconr-inspector-desktop.png",
    fullPage: true,
  });
  expect(failures).toEqual([]);
});

test("mobile layout and empty search", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByRole("textbox", { name: "Search knowledge" })
    .fill("qzxnonexistent");
  await page.getByRole("button", { name: "Run search", exact: true }).click();
  await expect(page.getByText("No matching source entries.")).toBeVisible();
  const width = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(width).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: "/tmp/navconr-inspector-mobile.png",
    fullPage: true,
  });
});

test("semantic maps and relationship provenance filters", async ({ page }) => {
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Map organization" })
    .selectOption("semantic");
  await page
    .locator(".tree-row")
    .filter({ hasText: "Token lifecycle" })
    .click();
  await page
    .getByRole("combobox", { name: "Relationship type" })
    .selectOption("member");
  await expect(page.locator(".related")).toHaveCount(2);
  await page
    .getByRole("combobox", { name: "Relationship origin" })
    .selectOption("parsed");
  await expect(page.locator(".related")).toHaveCount(0);
  await page
    .getByRole("combobox", { name: "Relationship origin" })
    .selectOption("manual");
  await expect(page.locator(".related")).toHaveCount(2);
});
