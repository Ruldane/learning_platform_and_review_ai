import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_DECISION_LAB !== "1", "Requiert la pile synthétique du laboratoire.");

test("compare deux architectures et retrouve un scénario sauvegardé", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/learn/decisions");
  const rate = page.getByLabel("Charge (requêtes par seconde)");
  await expect(page.getByRole("heading", { name: "Laboratoire de décisions" })).toBeVisible();
  await rate.fill("150");
  await page.getByRole("button", { name: "Comparer", exact: true }).click();
  const measures = page.getByRole("region", { name: "Résultats de la simulation" });
  const format = new Intl.NumberFormat("fr-FR");
  await expect(measures.getByText(format.format(300_000), { exact: true })).toBeVisible();
  await expect(measures.getByText(format.format(396_000), { exact: true })).toBeVisible();

  await page.getByLabel("Nom du scénario").fill("Comparer à 150 requêtes par seconde");
  await page.getByLabel("Critique ou décision (facultative)").fill("Vérifier le budget.");
  await page.getByRole("button", { name: "Sauvegarder", exact: true }).click();
  await expect(page.getByText("Scénario sauvegardé.")).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: /Comparer à 150 requêtes par seconde/ }).click();
  await expect(rate).toHaveValue("150");
  await expect(measures.getByText(format.format(396_000), { exact: true })).toBeVisible();
  await expect(page.getByLabel("Critique ou décision (facultative)")).toHaveValue("Vérifier le budget.");
});
