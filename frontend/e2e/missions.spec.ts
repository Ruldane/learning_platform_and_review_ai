import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_MISSIONS !== "1", "Utilise une offre fictive sur une base jetable.");

const REQUIREMENT = "Construire une transformation Python réutilisable.";
const OTHER_REQUIREMENT = "Documenter et contrôler les valeurs manquantes.";
const NOTE = "Le cas courant produit les totaux attendus.";
const ARTIFACT = "Compte rendu du prototype et résultats observés sur les deux cas.";

test("crée la mission depuis l’offre et retrouve sa mesure et sa preuve après rechargement", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const postings = await request.get(`${API}/postings`);
  expect(postings.ok()).toBe(true);
  const offers: { id: string; title: string }[] = await postings.json();
  const posting = offers.find((row) => row.title === "Ingénierie des données");
  if (!posting) throw new Error("Offre de recette absente.");

  await page.goto(`/carriere/offres/${posting.id}`);
  await page.getByRole("link", { name: "Ouvrir Mission 48 h" }).press("Enter");
  await page.getByRole("checkbox", { name: REQUIREMENT }).check();
  await page.getByRole("button", { name: "Créer la mission" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Mission 48 h" })).toBeFocused();
  await expect(page.getByRole("heading", { name: OTHER_REQUIREMENT })).toHaveCount(0);

  await page.getByLabel("Cas validés").selectOption("1");
  await page.getByLabel("Mesures et résultats observés").fill(NOTE);
  await page.getByRole("button", { name: "Enregistrer le critère" }).press("Enter");
  await expect(page.getByText("Critère enregistré.")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: REQUIREMENT })).toBeVisible();
  await expect(page.getByLabel("Cas validés")).toHaveValue("1");
  await expect(page.getByLabel("Mesures et résultats observés")).toHaveValue(NOTE);
  await expect(
    page.getByRole("button", { name: "Enregistrer le rendu et la preuve" }),
  ).toBeDisabled();

  await page.getByLabel("Cas validés").selectOption("2");
  await page.getByRole("button", { name: "Enregistrer le critère" }).press("Enter");
  await expect(page.getByText("Objectif atteint", { exact: false })).toBeVisible();
  await page.getByLabel("Rendu privé du projet").fill(ARTIFACT);
  await page.getByRole("button", { name: "Enregistrer le rendu et la preuve" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Preuve de rendu" })).toBeVisible();
  await page.reload();
  await expect(page.getByText(ARTIFACT, { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Preuve de rendu" })).toBeVisible();
});
