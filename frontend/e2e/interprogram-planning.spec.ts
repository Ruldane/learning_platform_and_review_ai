import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_INTERPROGRAM_PLANNING !== "1", "Utilise une base de programmes fictifs.");

test("prépare puis applique une semaine qui tient compte des prérequis et de la réservation", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/etudier/planning-commun");
  await expect(page.getByRole("heading", { name: "Planning entre programmes" })).toBeVisible();

  await page.getByLabel("Lundi de la semaine").fill("2030-01-07");
  await page.getByRole("checkbox", { name: "Standardiser les entrées" }).check();
  await page.getByRole("checkbox", { name: "Analyser un relevé" }).check();
  await page.getByRole("button", { name: "Préparer la semaine commune" }).press("Enter");

  const week = page.getByRole("region", { name: "Semaine du 7 janv. 2030" });
  const monday = week.getByRole("row", { name: /7 janv. 2030/ });
  await expect(monday.getByRole("cell", { name: "60" })).toBeVisible();
  await expect(monday.getByRole("cell", { name: "30" })).toBeVisible();
  await expect(week.getByText("Standardiser les entrées · 8 janv. 2030 · 45 min")).toBeVisible();
  await expect(week.getByText("Analyser un relevé · 9 janv. 2030 · 45 min")).toBeVisible();
  await expect(
    week.getByText("Module de référence prévu plus tôt", { exact: false }),
  ).toBeVisible();
  await expect(week.getByText("À valider", { exact: false })).toBeVisible();

  await week.getByRole("button", { name: "Appliquer cette semaine" }).press("Enter");
  await expect(week.getByRole("heading", { name: "Semaine du 7 janv. 2030" })).toBeFocused();
  await expect(week.getByText("Semaine appliquée", { exact: false })).toBeVisible();
  await page.reload();
  await expect(week.getByText("Semaine appliquée", { exact: false })).toBeVisible();
  await expect(week.getByRole("button", { name: "Appliquer cette semaine" })).toHaveCount(0);
});
