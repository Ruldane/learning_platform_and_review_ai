import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.beforeEach(({ request }) => finishFirstLaunch(request));

test("le training persiste le fil et applique un nouveau mode sans choisir de leçon", async ({
  page,
}) => {
  await page.goto("/etudier/training");
  await page.getByRole("button", { name: "Commencer le training" }).click();
  await expect(page).toHaveURL(/\/etudier\/training\/[0-9a-f-]+$/);
  const url = page.url();
  const mode = page.getByRole("combobox", { name: "Mode d’apprentissage" });
  await expect(mode).toHaveValue("socratic");
  await mode.selectOption("direct");
  await expect(mode).toHaveValue("direct");

  const question = page.getByRole("textbox", { name: "Ton message au tuteur" });
  await question.fill("Je veux comprendre comment composer des chaînes.");
  await question.press("Enter");
  const reply = page.getByText("Une chaîne relie une étape à la suivante. Propose un exemple.");
  await expect(reply).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(url);
  await expect(reply).toBeVisible();
  await expect(mode).toHaveValue("direct");

  await page.getByRole("button", { name: "Terminer le training" }).click();
  await expect(page.getByRole("heading", { name: "Bilan du training" })).toBeVisible();
  await expect(reply).toBeVisible();
});
