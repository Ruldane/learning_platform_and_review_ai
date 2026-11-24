import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_STUDY_RETURN !== "1", "Utilise uniquement des repères d’étude fictifs.");

test("relit le rappel et les repères, ouvre le bloc et conserve les tâches du programme", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const list = await request.get(`${API}/programs`);
  expect(list.ok()).toBe(true);
  const programs: { id: string; title: string }[] = await list.json();
  const program = programs.find((item) => item.title === "Tâche déjà planifiée");
  if (!program) throw new Error("Programme de recette absent.");
  const path = `${API}/programs/${program.id}`;
  const first = await request.get(path);
  expect(first.ok()).toBe(true);
  const existing = await first.json();

  await page.goto("/study/return");
  await page.getByLabel("Date du rappel").fill("2026-01-05");
  await page.getByRole("button", { name: "Programmer le rappel" }).press("Enter");
  await expect(page.getByText("Le rappel de reprise est dû.")).toBeVisible();
  await page.getByRole("button", { name: "Préparer mon bloc de reprise" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Mon bloc de reprise" })).toBeVisible();

  await page.reload();
  await expect(page.getByText("Le rappel de reprise est dû.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Étudier, Un rappel de reprise" })).toBeVisible();
  await expect(page.getByText("Validation des données", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Comment reconnaître une donnée manquante ?", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dernier bloc terminé" })).toBeVisible();

  await page.getByRole("button", { name: "Démarrer le bloc" }).press("Enter");
  await expect(page).toHaveURL(/\/study\/training\/[0-9a-f-]+$/);
  const trainingUrl = new URL(page.url()).pathname;
  await page.goto("/study/return");
  await expect(page.getByRole("link", { name: "Retrouver le bloc" })).toHaveAttribute(
    "href",
    trainingUrl,
  );
  await expect(page.getByText("Le rappel de reprise est dû.")).toHaveCount(0);
  const unchanged = await request.get(path);
  expect(unchanged.ok()).toBe(true);
  expect(await unchanged.json()).toEqual(existing);
});
