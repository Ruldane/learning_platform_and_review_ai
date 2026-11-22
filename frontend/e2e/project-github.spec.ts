import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_PROJECT_GITHUB_FIXTURES !== "1",
  "Utilise GitHub et le Praticien fictifs.",
);

const backend = process.env.E2E_API_URL ?? "http://localhost:8809";
const fixtures = `${backend}/__e2e/project-github`;
const repository = "https://github.com/orga-fictive/bibliotheque";
const sha = "128d4898ea3ef79a06720eabe0b041b1a9c2553d";

test("rendre le projet avec un commit attribué et retrouver la preuve sur la carte", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const seeded = await request.post(`${fixtures}/seed`);
  expect(seeded.ok()).toBe(true);
  const { project_id: id } = (await seeded.json()) as { project_id: string };
  const project = `/competences/portfolio/${id}`;
  await page.goto(project);
  await page.getByRole("textbox", { name: "Lien du dépôt" }).fill(repository);
  await page.getByText("Faire vérifier un commit GitHub", { exact: true }).press("Enter");
  await page.getByRole("textbox", { name: "SHA complet du commit" }).fill(sha);
  await page.getByRole("button", { name: "Créer le code de vérification" }).press("Enter");
  const token = page.locator("code").filter({ hasText: /^tremplin:/ });
  await expect(token).toBeVisible();
  const code = await token.textContent();
  expect((await request.post(`${fixtures}/profile`, { data: { code } })).ok()).toBe(true);
  await page.getByRole("button", { name: "Rendre le projet" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Commits GitHub vérifiés" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Ouvrir le commit 128d4898 sur GitHub" }),
  ).toHaveAttribute("href", `${repository}/commit/${sha}`);

  await page.goto("/competences");
  await page.getByRole("button", { name: /^pandas[,. ]/i }).press("Enter");
  const proof = page.getByRole("link", { name: /Contribution GitHub vérifiée \(128d4898\)/ });
  await expect(proof).toHaveAttribute("href", project);
  await proof.press("Enter");
  await expect(page.getByRole("heading", { name: "Commits GitHub vérifiés" })).toBeVisible();
});
