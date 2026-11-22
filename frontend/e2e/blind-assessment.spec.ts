import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_BLIND_ASSESSMENT !== "1", "Requiert le Vérificateur synthétique.");

test("fige deux versions de CV et ouvre leurs sources après le verdict", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const seed = await request.post(`${new URL(API).origin}/e2e/blind-assessment/ready`);
  expect(seed.ok()).toBe(true);
  const { version_ids: versions } = (await seed.json()) as { version_ids: [string, string] };
  await page.goto("/carriere/epreuve-aveugle");
  await expect(page.getByRole("heading", { name: "Épreuve en aveugle" })).toBeVisible();
  await page.getByLabel("Première version de CV").selectOption(versions[0]);
  await page.getByLabel("Seconde version de CV").selectOption(versions[1]);
  await page.getByLabel("Grille d’évaluation").selectOption({ label: "Clarté de lecture" });
  await page.getByRole("button", { name: "Figer les versions et la grille" }).press("Enter");

  const links = page.getByRole("link", { name: /Ouvrir le PDF du texte [AB]/ });
  await expect(page.getByRole("button", { name: "Lancer l’évaluation" })).toBeVisible();
  await expect(links).toHaveCount(0);
  await page.getByRole("button", { name: "Lancer l’évaluation" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Verdict" })).toBeVisible();
  await expect(page.getByText("Le texte B obtient le meilleur score.")).toBeVisible();

  await page.reload();
  await expect(links).toHaveCount(2);
  const destinations = await links.evaluateAll((items) => items.map((item) => item.getAttribute("href")));
  expect(new Set(destinations)).toEqual(new Set(versions.map((id) => `${API}/cv/versions/${id}/pdf`)));
  const download = page.waitForEvent("download");
  await links.first().press("Enter");
  expect((await download).suggestedFilename()).toMatch(/^cv-[12]\.pdf$/);
});
