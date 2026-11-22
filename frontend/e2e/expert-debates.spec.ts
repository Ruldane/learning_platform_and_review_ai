import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_EXPERT_DEBATES_FIXTURES !== "1",
  "Utilise le serveur de recette du débat.",
);

const question = "Quel tri stable choisir pour un petit jeu de données ?";
const judgment = "Je choisis le tri stable et je vérifierai la taille des données.";
const source = "https://sources-debat.example.test/methode";

test("le débat ouvre une source au clavier et retrouve le jugement", async ({
  page,
  context,
  request,
}) => {
  await context.route(source, (route) =>
    route.fulfill({
      contentType: "text/html; charset=utf-8",
      body: "<h1>Méthode fictive</h1>",
    }),
  );
  await finishFirstLaunch(request);
  await page.goto("/etudier/debats");
  const input = page.getByRole("textbox", { name: "Ta question" });
  await input.fill(question);
  await page.getByRole("button", { name: "Lancer le débat" }).press("Enter");
  await expect(page).toHaveURL(/\/etudier\/debats\/[0-9a-f-]+$/);
  const expert = page.getByRole("article", { name: "Chercheur" });
  const reference = expert.getByRole("link", { name: /Méthode de comparaison/ });
  await expect(reference).toBeVisible();
  const [opened] = await Promise.all([context.waitForEvent("page"), reference.press("Enter")]);
  await expect(opened.getByRole("heading", { name: "Méthode fictive" })).toBeVisible();
  await opened.close();

  await page.getByRole("textbox", { name: "Ton jugement" }).fill(judgment);
  await page.getByRole("button", { name: "Enregistrer mon jugement" }).press("Enter");
  await expect(page.getByText("Jugement enregistré.")).toBeVisible();
  await page.goto("/etudier/debats");
  await page.getByRole("link", { name: question, exact: true }).press("Enter");
  await expect(page.getByRole("textbox", { name: "Ton jugement" })).toHaveValue(judgment);
});
