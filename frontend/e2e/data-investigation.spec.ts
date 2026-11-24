import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_DATA_INVESTIGATION !== "1", "Requiert la base locale de recette.");

test("rejoue les transformations à partir des lignes sources", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/study/investigations");
  await page
    .getByRole("region", { name: "Contrôle des livraisons d’un festival" })
    .getByRole("button", { name: "Ouvrir cette enquête" })
    .click();
  for (const title of [
    "Garder la dernière révision par référence",
    "Garder les livraisons terminées",
    "Écarter les lignes sans référence",
    "Écarter les quantités nulles ou négatives",
  ]) {
    await page.getByRole("button", { name: title }).click();
    await expect(page.getByRole("button", { name: title })).toBeDisabled();
  }
  await expect(page.getByText("3 lignes retenues · 22 unités", { exact: true })).toBeVisible();
  await page.getByLabel("Nombre de livraisons retenues").fill("3");
  await page.getByLabel("Total des unités").fill("22");
  await page.getByRole("button", { name: "Remettre l’enquête" }).click();
  await expect(page.getByText("La chaîne préserve l’intégrité des données.")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Résultat de référence · 3 livraisons et 22 unités")).toBeVisible();
  await expect(page.getByText(/Empreinte du jeu source/)).toBeVisible();
});
