import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_HUNT !== "1", "Requiert le serveur synthétique tests.e2e.lesson_hunt.");

test("repère deux erreurs dans la copie et retrouve la leçon publiée", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/learn/lessons");
  await page.getByRole("link", { name: "Lire « Module Bases »", exact: true }).click();
  const lesson = page.url();
  await expect(page.getByText("Un tuple est immuable.", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Chasse aux erreurs" }).click();
  await page.getByRole("button", { name: "Préparer la copie" }).press("Enter");
  await expect(page.getByText("Un tuple est modifiable.", { exact: true })).toBeVisible();
  await expect(page.getByText("Un ensemble conserve les doublons.", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Bilan de la chasse" })).toHaveCount(0);

  await page
    .getByRole("textbox", { name: "Première erreur et explication" })
    .fill("Le tuple est immuable après sa création.");
  await page
    .getByRole("textbox", { name: "Seconde erreur et explication" })
    .fill("Un ensemble élimine les doublons.");
  await page.getByRole("button", { name: "Vérifier mes réponses" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Bilan de la chasse" })).toBeVisible();
  await expect(
    page.getByText("Tu as repéré l’immuabilité du tuple.", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Bilan de la chasse" })).toBeVisible();
  await page.goto(lesson);
  await expect(page.getByText("Un tuple est immuable.", { exact: true })).toBeVisible();
  await expect(page.getByText("Un ensemble élimine les doublons.", { exact: true })).toBeVisible();
});
