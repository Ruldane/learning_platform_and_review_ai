import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_MENTOR_REVIEWS !== "1", "Requiert un dossier synthétique côté serveur.");

const PACKET = "Dossier synthétique du mentor";
const ARTIFACT = "Le prototype fictif traite les deux exemples attendus.";
const COMMENT = "Ajouter une note sur les deux résultats.";

test("confirme une copie, recueille un commentaire et retire l’accès", async ({ page, request, browser }) => {
  await finishFirstLaunch(request);
  await page.goto("/carriere/relecture-mentor");
  await page.getByLabel("Dossier à partager").selectOption({ label: PACKET });
  await page.getByRole("button", { name: "Préparer le partage" }).click();
  await expect(page.getByText(ARTIFACT)).toBeVisible();
  await page.getByRole("button", { name: "Confirmer le partage" }).click();
  const link = await page.getByLabel("Lien de partage").inputValue();
  expect(new URL(link).search).toBe("");
  expect(new URL(link).hash.length).toBeGreaterThan(20);

  const guest = await browser.newPage();
  try {
    await guest.goto(link);
    await expect(guest.getByText(ARTIFACT)).toBeVisible();
    await guest.getByLabel("Commentaire", { exact: true }).fill(COMMENT);
    await guest.getByRole("button", { name: "Envoyer le commentaire" }).click();
    await expect(guest.getByText("Commentaire envoyé.")).toBeVisible();

    await page.getByRole("button", { name: new RegExp(PACKET) }).click();
    await expect(page.getByText(COMMENT)).toBeVisible();
    await page.getByRole("button", { name: "Retirer l’accès" }).click();
    await expect(page.getByText("Accès retiré", { exact: true })).toBeVisible();

    await guest.reload();
    await expect(guest.getByText("Ce lien de relecture est invalide, expiré ou retiré.")).toBeVisible();
    await expect(guest.getByText(ARTIFACT)).toHaveCount(0);
  } finally {
    await guest.close();
  }
});
