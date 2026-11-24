import { expect, test, type Page } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_RECRUITMENT_PROCESS !== "1", "Requiert le Vérificateur synthétique.");

function stage(page: Page, label: string) {
  return page.locator("article").filter({ has: page.getByRole("heading", { name: label, exact: true }) });
}

async function answer(page: Page, label: string, text: string) {
  const panel = stage(page, label);
  await panel.getByRole("textbox", { name: "Ta réponse" }).fill(text);
  await panel.getByRole("button", { name: "Envoyer pour évaluation" }).press("Enter");
}

test("reprend le recrutement à l’exercice et retrouve les trois appréciations", async ({ page, request }) => {
  await finishFirstLaunch(request);
  const seeded = await request.post(`${new URL(API).origin}/e2e/recruitment-process/ready`);
  expect(seeded.ok()).toBe(true);
  const { posting_id: posting, project_id: project } = (await seeded.json()) as {
    posting_id: string; project_id: string;
  };
  await page.goto("/career/recruitment-process");
  await page.getByLabel("Offre analysée").selectOption(posting);
  await page.getByLabel("Projet revu à présenter").selectOption(project);
  await page.getByRole("button", { name: "Préparer la répétition" }).press("Enter");
  await expect(page.getByRole("link", { name: "Audit des délais d’un pipeline" })).toHaveAttribute(
    "href", `/skills/portfolio/${project}`,
  );
  await expect(page.getByText("Justifier la fidélité d’un système RAG", { exact: false })).toBeVisible();
  await answer(page, "Revue de projet", "J’ai contrôlé les mesures d’un échantillon daté.");
  await expect(stage(page, "Exercice").getByRole("textbox", { name: "Ta réponse" })).toBeVisible();

  await page.reload();
  await expect(page.getByText("Le projet contient des mesures vérifiables.")).toBeVisible();
  await answer(page, "Exercice", "Je compare une mesure témoin avec et sans la correction.");
  await answer(page, "Entretien", "Je présente les écarts et j’explicite la taille de l’échantillon.");
  await expect(page.getByText("Répétition terminée")).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Appréciation", exact: true })).toHaveCount(3);
  await expect(page.getByText("La réponse d’entretien précise une limite.")).toBeVisible();
});
