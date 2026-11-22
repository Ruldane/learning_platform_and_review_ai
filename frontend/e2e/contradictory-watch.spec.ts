import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_CONTRADICTORY_WATCH !== "1", "Requiert la base locale de recette.");

test("fige deux sources puis consigne une mesure inconclusive", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/etudier/veille-contradictoire");
  await page.getByLabel("Nom de l’expérience").fill("Latence de rendu");
  const first = page.getByRole("group", { name: "Première source" });
  await first.getByLabel("Lien de la source").fill("https://example.org/documentation");
  await first.getByLabel("Version ou date de consultation").fill("Version 1.2");
  await first.getByLabel("Affirmation à tester").fill("Le rendu dure moins de 80 ms.");
  const second = page.getByRole("group", { name: "Seconde source" });
  await second.getByLabel("Lien de la source").fill("https://example.net/mesures");
  await second.getByLabel("Version ou date de consultation").fill("Version 2.1");
  await second.getByLabel("Affirmation à tester").fill("Le rendu dure au moins 100 ms.");
  await page.getByLabel("Protocole local").fill("Charger le même fichier dix fois.");
  await page.getByLabel("Critère décidé avant le test").fill("Mesurer la médiane.");
  await page.getByRole("button", { name: "Figer les sources et le protocole" }).click();
  await expect(page.getByRole("heading", { name: "Latence de rendu" })).toBeVisible();
  await expect(page.getByText("Version 2.1")).toBeVisible();
  await page.getByLabel("Mesure ou observation").fill("92 ms");
  await page.getByLabel("Conclusion selon le critère").selectOption("inconclusive");
  await page.getByRole("button", { name: "Figer le résultat" }).click();
  await expect(page.getByRole("heading", { name: "Résultat enregistré" })).toBeVisible();
  await page.reload();
  await expect(page.getByText("92 ms")).toBeVisible();
  await expect(page.getByText("L’expérience ne départage pas les affirmations")).toBeVisible();
  await expect(page.getByText("Version 1.2")).toBeVisible();
});
