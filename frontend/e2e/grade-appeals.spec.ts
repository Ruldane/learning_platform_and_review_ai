import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_GRADE_APPEALS !== "1", "Requiert un second lecteur synthétique.");

test("justifie un désaccord puis retrouve la décision et les deux lectures", async ({ page, request }) => {
  await finishFirstLaunch(request);
  const seed = await request.post(`${new URL(API).origin}/e2e/grade-appeals/ready`);
  expect(seed.ok()).toBe(true);
  const { project_id: project } = (await seed.json()) as { project_id: string };
  await page.goto("/competences/contestations");
  await page.getByLabel("Projet évalué").selectOption(project);
  await page.getByLabel("Critère contesté").selectOption({ label: "Rendre le prélèvement reproductible" });
  const reason = "Les dates se trouvent dans le dernier paragraphe de la remise.";
  await page.getByLabel("Motif du désaccord").fill(reason);
  await page.getByRole("button", { name: "Enregistrer le désaccord" }).press("Enter");

  await expect(page.getByRole("heading", { name: "Première lecture" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Seconde lecture" })).toHaveCount(0);
  await page.locator("summary").filter({ hasText: "Remise figée" }).press("Enter");
  await expect(page.getByText("Le protocole fixe trois lectures", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Demander une seconde lecture" }).press("Enter");
  await expect(page.getByText("La seconde lecture confirme", { exact: false })).toBeVisible();
  await expect(page.getByText("La première lecture ne retrouve pas", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Retenir la seconde lecture" }).press("Enter");
  await expect(page.getByText("Décision finale enregistrée")).toBeVisible();

  await page.reload();
  await expect(page.getByText("Seconde lecture retenue")).toBeVisible();
  await expect(page.getByText(reason)).toBeVisible();
  await page.getByRole("link", { name: "Retour aux contestations" }).press("Enter");
  await expect(page.getByRole("link", { name: /Journal de mesures/ })).toBeVisible();
});
