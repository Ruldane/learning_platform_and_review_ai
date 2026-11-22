import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_PAPER_LAB !== "1",
  "Requiert le serveur synthétique tests.e2e.paper_lab.",
);

test("lit une source, ouvre le mini-cours et joue la mesure du notebook", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/apprendre/articles");
  await page
    .getByRole("textbox", { name: "Adresse de l’article" })
    .fill("https://articles.exemple.org/regression");
  await page.getByRole("button", { name: "Préparer le mini-cours" }).press("Enter");
  await expect(
    page.getByRole("heading", { name: "Mesurer une pente sur des points" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Mesurer une pente sur des points" }),
  ).toHaveAttribute("href", "https://articles.exemple.org/regression");
  await expect(page.getByText("La pente estimée vaut 2,0 sur les points générés.")).toBeVisible();

  await expect(page.locator('blockquote')).toContainText("L'expérience de démonstration obtient une pente de 2,0.");
  await page.getByRole("link", { name: "Ouvrir le projet Python" }).press("Enter");
  await page.getByRole("button", { name: /experience\.ipynb/ }).press("Enter");
  await expect(page.getByRole("textbox", { name: "Source de la cellule 2" })).toHaveValue(/print/);
  await page.getByRole("button", { name: "Exécuter la cellule 2" }).press("Enter");
  await expect(page.getByRole("log", { name: "Sortie de la cellule" })).toHaveText("2.0");
});
