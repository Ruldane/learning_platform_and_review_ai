import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_PROJECT_HANDOFFS !== "1", "Requiert un projet fictif déjà rendu.");

test("approuve le guide d’un rendu existant et exporte la version exacte", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/carriere/transmission-projet");
  await page.getByRole("combobox", { name: "Projet", exact: true })
    .selectOption({ label: "Catalogue de la bibliothèque" });
  const submitted = "Le rendu synthétique garde la liste des livres et son filtre.";
  const commands = "python -m pytest tests/test_catalogue.py";
  const limitations = "Le jeu de données est fictif.";
  const steps = "Ouvrir la liste, puis rechercher un livre par son titre.";
  await expect(page.getByText(submitted, { exact: true })).toBeVisible();
  await page.getByLabel("Commandes de recette").fill(commands);
  await page.getByLabel("Limites connues").fill(limitations);
  await page.getByLabel("Étapes de prise en main").fill(steps);
  await page.getByRole("button", { name: "Prévisualiser le guide" }).click();
  await expect(page.getByRole("heading", { name: "Aperçu du guide" })).toBeFocused();
  await expect(page.getByRole("code").filter({ hasText: commands })).toBeVisible();
  const exportButton = page.getByRole("button", { name: "Exporter le guide" });
  await expect(exportButton).toHaveCount(0);
  const revision = await page.getByText(/^[a-f0-9]{64}$/).textContent();
  if (!revision) throw new Error("La recette attend une empreinte de l’aperçu.");
  await page.getByRole("button", { name: "Approuver cette version" }).click();
  await expect(page.getByRole("heading", { name: "Version approuvée" })).toBeVisible();
  await page.reload();
  await expect(exportButton).toBeVisible();
  const [download] = await Promise.all([page.waitForEvent("download"), exportButton.click()]);
  expect(download.suggestedFilename()).toBe("guide-de-reprise.md");
  const path = await download.path();
  if (!path) throw new Error("Le téléchargement n’a pas produit de fichier.");
  const file = await readFile(path);
  expect(createHash("sha256").update(file).digest("hex")).toBe(revision);
  for (const text of [submitted, commands, limitations, steps]) {
    expect(file.toString("utf-8")).toContain(text);
  }
});
