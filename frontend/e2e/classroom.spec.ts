import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_CLASSROOM !== "1",
  "Requiert le serveur synthétique tests.e2e.classroom.",
);

test("explique la leçon, retrouve les trois camarades et ouvre leur source", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/learn/lessons");
  await page.getByRole("link", { name: "Lire « Module Bases »", exact: true }).click();
  await expect(page).toHaveURL(/\/learn\/lessons\/[0-9a-f-]+$/);
  const lesson = page.url();
  await page.getByRole("link", { name: "Entrer en classe virtuelle" }).click();
  await expect(page).toHaveURL(lesson + "/classroom");

  const input = page.getByRole("textbox", { name: "Ton explication" });
  await expect(input).toBeEnabled();
  await input.fill("Ces deux étapes forment une chaîne.");
  await input.press("Enter");
  const thread = page.getByRole("log", { name: "Discussion de classe" });
  await expect(thread.getByText("Tu peux me donner un exemple concret ?")).toBeVisible();
  await expect(thread.getByText("Comment distingues-tu les deux étapes ?")).toBeVisible();
  await expect(
    thread.getByText("Dans quel cas ton raisonnement atteint-il sa limite ?"),
  ).toBeVisible();

  await page.reload();
  for (const label of ["Camarade débutant", "Camarade de ton niveau", "Camarade avancé"]) {
    await expect(thread.getByText(label)).toBeVisible();
  }
  await thread.getByRole("link", { name: "Module Bases", exact: true }).click();
  await expect(page).toHaveURL(lesson);
  await expect(page.getByText("Texte.", { exact: true })).toBeVisible();
});
