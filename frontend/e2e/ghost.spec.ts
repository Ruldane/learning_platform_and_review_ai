import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_GHOST !== "1", "Requiert le serveur synthétique tests.e2e.ghost.");

test("relit un ancien résumé et compare un quiz sans révéler ses anciennes réponses", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/study/journal");
  await page.getByRole("link", { name: "Courir contre cette tentative" }).first().click();
  const ghost = page.getByRole("region", { name: "Course contre ton fantôme" });
  await expect(ghost.getByText("Ton essai précédent")).toBeVisible();
  await expect(ghost.getByText("71 s")).toBeVisible();
  await expect(ghost.getByText("Ton essai en cours")).toBeVisible();

  const choices = ghost.getByRole("combobox", { name: "Tentative de référence" });
  await choices.focus();
  await choices.press("End");
  await expect(ghost.getByText(/Version inconnue/)).toBeVisible();
  await expect(ghost.getByText("90 %")).toBeVisible();
  await expect(ghost.getByText("Ton essai en cours")).toHaveCount(0);
  await choices.press("ArrowUp");

  await page
    .getByRole("textbox", { name: /réponse à la question/i })
    .first()
    .fill("Un index.");
  await expect(ghost.getByText("1 / 10", { exact: true })).toBeVisible();
  await expect(ghost.getByRole("timer")).not.toHaveText("0 s");
  const quiz = page.url().split("/").at(-1)?.split("?")[0];
  const history = await request.get(`${API}/quizzes/${quiz}/ghost`);
  expect(history.ok()).toBe(true);
  expect(await history.text()).not.toContain("Texte historique synthétique");
  await expect(page.getByText(/Texte historique synthétique/)).toHaveCount(0);

  await page.getByRole("button", { name: "Envoyer", exact: true }).press("Enter");
  await page.getByRole("button", { name: "Envoyer quand même" }).press("Enter");
  await expect(ghost.getByText("Ton nouvel essai")).toBeVisible();
  await expect(ghost.getByText("Ton essai précédent")).toBeVisible();
});
