import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_SKILL_MARKET !== "1",
  "Requiert le serveur synthétique tests.e2e.skill_market.",
);

test("compare la demande puis ouvre le chapitre de la simulation", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/career/skills");
  await page.getByRole("textbox", { name: "Poste visé" }).fill("Ingénieur IA");
  await page.getByRole("textbox", { name: "Zone" }).fill("France");
  await page.getByRole("button", { name: "Comparer les relevés" }).press("Enter");

  const row = page.getByRole("row").filter({ has: page.getByRole("rowheader", { name: "RAG" }) });
  await expect(row.getByText("50 %", { exact: true })).toBeVisible();
  await expect(row.getByText("+25", { exact: true })).toBeVisible();
  await row.getByRole("button", { name: "Simuler une heure sur RAG" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Une heure sur RAG" })).toBeVisible();
  await expect(page.getByText(/Une heure couvre 50 % des 120 minutes/)).toBeVisible();
  await page.getByRole("link", { name: "Ouvrir le chapitre" }).press("Enter");
  await expect(page).toHaveURL(/\/learn\/lessons\/[0-9a-f-]+$/);
});
