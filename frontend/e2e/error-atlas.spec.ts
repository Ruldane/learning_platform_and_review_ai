import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_ERROR_ATLAS !== "1",
  "Utilise des corrections fictives et une base jetable.",
);

const HYPOTHESIS = "Valeurs manquantes";
const QUIZ = "Quiz · Quiz sur les données manquantes";
const PROJECT = "Projet · Contrôle d’un jeu de données";

test("relie deux corrections à un prérequis et retrouve l’exercice choisi", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/study/error-atlas");
  await expect(page.getByRole("heading", { name: "Atlas des erreurs" })).toBeVisible();

  const evidence = page.getByLabel("Erreur observée");
  const quiz = await evidence.getByRole("option", { name: new RegExp(QUIZ) }).getAttribute("value");
  const project = await evidence
    .getByRole("option", { name: new RegExp(PROJECT) })
    .getAttribute("value");
  if (!quiz || !project) throw new Error("Corrections de recette absentes.");

  await evidence.selectOption(quiz);
  await page.getByLabel("Prérequis supposé").fill(HYPOTHESIS);
  await page.getByRole("button", { name: "Enregistrer l’observation" }).press("Enter");
  const group = page.getByRole("region", { name: HYPOTHESIS });
  await expect(group.getByText("1 observation", { exact: false })).toBeVisible();
  await expect(group.getByText(QUIZ, { exact: true })).toBeVisible();

  await evidence.selectOption(project);
  await page.getByLabel("Prérequis supposé").fill("valeurs  MANQUANTES");
  await page.getByLabel("Degré de confiance").selectOption("high");
  await page.getByRole("button", { name: "Enregistrer l’observation" }).press("Enter");
  await expect(group.getByText("2 observations", { exact: false })).toBeVisible();
  await expect(group.getByText("Variable selon les observations", { exact: false })).toBeVisible();
  await expect(group.getByRole("link", { name: "Voir la source" })).toHaveCount(2);

  await group.getByRole("button", { name: "Choisir cet exercice correctif" }).press("Enter");
  await expect(group.getByRole("heading", { name: HYPOTHESIS })).toBeFocused();
  await expect(group.getByRole("heading", { name: "Exercice correctif" })).toBeVisible();
  await page.reload();
  await expect(group.getByRole("heading", { name: "Exercice correctif" })).toBeVisible();
  await expect(group.getByText("Construis un cas minimal", { exact: false })).toBeVisible();
  await group.getByText("Corrections utilisées", { exact: true }).click();
  await expect(group.getByRole("link", { name: "Voir la source" })).toHaveCount(4);
});
