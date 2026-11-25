import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.js";

test.skip(process.env.E2E_OFFER_COMPARISON !== "1", "Requiert deux offres privées fictives.");

test("règle les poids, compare deux offres et relit le scénario sauvegardé", async ({ page, request }) => {
  await finishFirstLaunch(request);
  const seed = await request.post(`${new URL(API).origin}/e2e/offer-comparison/ready`);
  expect(seed.ok()).toBe(true);
  const { first, second } = (await seed.json()) as { first: string; second: string };
  await page.goto("/career/offer-comparison");
  await page.getByLabel("Première offre").selectOption(first);
  await page.getByLabel("Deuxième offre").selectOption(second);
  await page.getByLabel("Mode de travail souhaité").selectOption("hybrid");
  await page.getByLabel("Lieu souhaité (libellé exact)").fill("Lyon");
  await page.getByLabel("Mode de travail", { exact: true }).fill("80");
  await page.getByLabel("Lieu", { exact: true }).fill("20");
  await page.getByRole("button", { name: "Enregistrer mes critères" }).press("Enter");
  await expect(page.getByText("Critères du compte enregistrés.")).toBeVisible();
  await page.getByRole("button", { name: "Calculer la comparaison" }).press("Enter");
  await expect(page.getByText("La première offre obtient le meilleur score.")).toBeVisible();
  await expect(page.getByText(/Faits manquants ou non interprétables/)).toHaveCount(2);
  await expect(page.getByRole("heading", { name: "Sensibilité aux poids" })).toBeVisible();
  await page.getByRole("button", { name: "Enregistrer le scénario" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Scénario enregistré" })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Score sur 100 · 80")).toBeVisible();
  await expect(page.getByText("Score sur 100 · 20")).toBeVisible();
  await page.getByRole("link", { name: "Retour à la comparaison d’offres" }).press("Enter");
  await expect(page.getByRole("link", { name: "Mesures A · Mesures B" })).toBeVisible();
  await expect(page.getByLabel("Mode de travail", { exact: true })).toHaveValue("80");
});
