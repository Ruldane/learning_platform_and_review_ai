import { expect, test, type Page } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_BOSS_FIXTURES !== "1", "Utilise le serveur de recette dédié au Boss.");

async function repairAndSave(page: Page): Promise<void> {
  await page.getByRole("link", { name: "Ouvrir le projet Python" }).click();
  await expect(
    page.getByRole("heading", { name: "Boss · Planificateur de demandes" }),
  ).toBeVisible();
  await page.locator(".monaco-editor .view-lines").first().click();
  await page.keyboard.press("Control+A");
  const saved = page.waitForResponse(
    (result) => result.request().method() === "PUT" && result.url().endsWith("/files"),
  );
  await page.keyboard.insertText(
    'def planifier(demandes):\n    return [d["id"] for d in sorted(demandes, key=lambda d: not d["urgente"])]\n',
  );
  expect((await saved).ok()).toBe(true);
  await page.goBack();
}

test("le Boss reprend le changement client et note la remise sauvegardée", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const programs = await request.get(`${API}/programs`);
  expect(programs.ok()).toBe(true);
  const [program] = (await programs.json()) as { id: string }[];
  if (!program) throw new Error("Programme de recette introuvable.");
  await page.goto(`/apprendre/programme/${program.id}`);
  await page.getByRole("link", { name: "Voir le Boss de fin de programme" }).click();
  await page.getByRole("button", { name: "Démarrer les 30 minutes" }).click();
  await expect(page.getByText("Demande initiale")).toBeVisible();
  const change = page.getByRole("heading", { name: "Changement demandé par le client" });
  await expect(change).toBeVisible();
  await page.reload();
  await expect(change).toBeVisible();

  await repairAndSave(page);
  await expect(change).toBeVisible();
  await page.getByRole("button", { name: "Remettre les fichiers sauvegardés" }).click();
  await expect(page.getByRole("heading", { name: "Grille d’évaluation" })).toBeVisible();
  await expect(page.getByText("18/20", { exact: true })).toBeVisible();
  const proof = page.getByText("Preuve ajoutée à ta carte des compétences.");
  await expect(proof).toBeVisible();
  await page.reload();
  await expect(proof).toBeVisible();
});
