import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

const FIXTURE = API.replace(/\/api\/v1$/, "/__e2e/contributions");
const PULL = "https://github.com/orga-fictive/bibliotheque/pull/12";

async function openSimulatedGitHub(page: Page): Promise<string> {
  let publicationBody = "";
  await page.context().route(/^https?:\/\/(?:[^/]+\.)?github\.com\//, async (route) => {
    const url = new URL(route.request().url());
    if (!url.pathname.startsWith("/orga-fictive/bibliotheque/compare/")) {
      await route.abort();
      return;
    }
    expect(decodeURIComponent(url.pathname)).toBe(
      "/orga-fictive/bibliotheque/compare/main...camille:fix/tests",
    );
    expect(url.searchParams.get("title")).toBe("Tests pandas");
    publicationBody = url.searchParams.get("body") ?? "";
    await route.fulfill({
      contentType: "text/html; charset=utf-8",
      body: "<h1>GitHub simulé</h1>",
    });
  });
  const [popup] = await Promise.all([
    page.waitForEvent("popup"),
    page.getByRole("link", { name: "Ouvrir GitHub pour publier" }).click(),
  ]);
  await expect(popup.getByRole("heading", { name: "GitHub simulé" })).toBeVisible();
  await popup.close();
  expect(publicationBody).toContain("Ajout des cas limites");
  expect(publicationBody).toContain("Closes #7");
  expect(publicationBody).toMatch(/<!-- tremplin-contribution:[0-9a-f-]+ -->/);
  return publicationBody;
}

async function checkProof(request: APIRequestContext, dossierPath: string) {
  const response = await request.get(`${API}/skills/graph`);
  expect(response.ok()).toBe(true);
  const graph = (await response.json()) as { nodes: { id: string; name: string; level: string }[] };
  const skill = graph.nodes.find((node) => node.name === "pandas");
  expect(skill?.level).toBe("proven");
  const detail = await request.get(`${API}/skills/${skill?.id}`);
  expect(detail.ok()).toBe(true);
  const { evidence } = (await detail.json()) as { evidence: { kind: string }[] };
  expect(evidence.filter(({ kind }) => kind === "contribution")).toEqual([
    expect.objectContaining({ label: "Tests pandas", url: dossierPath }),
  ]);
}

test("Contribution confirmée, publication simulée et preuve après fusion", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const seed = await request.post(`${FIXTURE}/seed`);
  expect(seed.ok()).toBe(true);
  const { program_id: programId } = (await seed.json()) as { program_id: string };

  await page.goto("/competences/contributions");
  await page.getByRole("combobox", { name: "Programme" }).selectOption(programId);
  await expect(page.getByRole("link", { name: "Tests pandas" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Tests numpy" })).toHaveCount(0);
  await page.getByRole("button", { name: "Ouvrir un dossier" }).click();
  await expect(page.getByRole("heading", { name: "Tests pandas", level: 1 })).toBeVisible();
  const dossierPath = new URL(page.url()).pathname;

  await page.getByLabel("Compte GitHub").fill("camille");
  await page.getByLabel("Branche à proposer").fill("fix/tests");
  await page.getByLabel("Description de la pull request").fill("Ajout des cas limites");
  const prepare = page.getByRole("button", { name: "Préparer la pull request" });
  await expect(prepare).toBeDisabled();
  await expect(page.getByRole("link", { name: "Ouvrir GitHub pour publier" })).toHaveCount(0);
  await page.getByRole("checkbox", { name: "Je confirme le texte et les branches." }).check();
  await prepare.press("Enter");
  await expect(page.getByText("Préparation confirmée", { exact: true })).toBeVisible();

  const body = await openSimulatedGitHub(page);
  expect((await request.post(`${FIXTURE}/pull`, { data: { body, merged: false } })).ok()).toBe(
    true,
  );
  await page.getByLabel("Adresse de la pull request publiée").fill(PULL);
  await page.getByRole("button", { name: "Vérifier et suivre" }).click();
  await expect(page.getByText("Pull request ouverte", { exact: true })).toBeVisible();
  await expect(page.getByText(/Proposition pour ton CV/)).toHaveCount(0);

  expect((await request.post(`${FIXTURE}/pull`, { data: { body, merged: true } })).ok()).toBe(true);
  await page.getByRole("button", { name: "Actualiser son statut" }).click();
  await expect(page.getByText(/Contribution acceptée/)).toBeVisible();
  await expect(page.getByText(/Proposition pour ton CV/)).toContainText("Tests pandas");
  await checkProof(request, dossierPath);
});
