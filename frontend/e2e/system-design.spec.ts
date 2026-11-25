import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_SYSTEM_DESIGN !== "1", "Requires the system design test server.");

test("draws, submits the saved diagram and revisits the review", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/applications/interview");
  await page.getByRole("link", { name: "System design practice" }).press("Enter");
  await page.getByRole("button", { name: "Open an architecture topic" }).press("Enter");
  await expect(
    page.getByRole("heading", { name: "Design a reminder service" }),
  ).toBeVisible();
  const rectangle = page.getByRole("radio", { name: "Rectangle", exact: true });
  await page.locator("label").filter({ has: rectangle }).click({ timeout: 30000 });
  await expect(rectangle).toBeChecked();
  const canvas = page.locator("canvas.excalidraw__canvas.interactive").first();
  await canvas.scrollIntoViewIfNeeded();
  const bounds = await canvas.boundingBox();
  if (!bounds) throw new Error("The architecture board did not appear.");
  await page.mouse.move(bounds.x + bounds.width * 0.4, bounds.y + bounds.height * 0.45);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * 0.58, bounds.y + bounds.height * 0.65, {
    steps: 10,
  });
  await page.mouse.up();
  await page.getByRole("button", { name: "Save the drawing" }).press("Enter");
  await expect(page.getByText("Saved version · 1")).toBeVisible();
  await page
    .getByRole("textbox", { name: "Defend your architecture choices" })
    .fill("A queue absorbs traffic spikes. An idempotency key prevents duplicate deliveries.");
  await page.getByRole("button", { name: "Submit the saved version" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Architecture review" })).toBeFocused();
  await expect(page.getByText("Submitted version · 1")).toBeVisible();
  await expect(page.getByText("Proof added to your skill map.")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Submitted version · 1")).toBeVisible();
});
