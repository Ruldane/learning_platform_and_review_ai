import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.beforeEach(({ request }) => finishFirstLaunch(request));

test("le training garde les leçons et le mode de chaque fil et permet de les effacer", async ({
  page,
  request,
}, testInfo) => {
  const api = process.env.E2E_API_URL ?? "http://localhost:8765";
  expect((await request.post(`${api}/__e2e/book/seed`)).ok()).toBe(true);
  await page.goto("/study/training");
  await page.getByText("Leçons sélectionnées (0)", { exact: true }).click();
  const select = page.getByRole("combobox", { name: "Ajouter une leçon" });
  await select.selectOption({ label: "Première boucle" });
  await expect(page.getByText("Leçons sélectionnées (1)", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Commencer le training" }).click();
  await expect(page).toHaveURL(/\/study\/training\/[0-9a-f-]+$/);
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

  const sidebar = page.getByRole("complementary", { name: "Conversations" });
  const title = sidebar.getByRole("textbox", { name: "Titre de la conversation" });
  await expect(title).toHaveValue(/Je veux comprendre/);
  await title.fill("Révision des chaînes");
  await sidebar.getByRole("button", { name: "Renommer" }).click();
  await expect(sidebar.getByRole("button", { name: "Ouvrir Révision des chaînes" })).toBeVisible();
  await sidebar.getByRole("button", { name: "Nouvelle conversation", exact: true }).click();
  await page.getByRole("button", { name: "Commencer le training" }).click();
  await expect(page).toHaveURL(/\/study\/training\/[0-9a-f-]+$/);
  await expect(page).not.toHaveURL(url);
  await expect(mode).toHaveValue("socratic");
  await expect(page.getByText("Leçons sélectionnées (0)", { exact: true })).toBeVisible();

  const search = sidebar.getByRole("searchbox", { name: "Rechercher un titre" });
  await search.fill("revision");
  await expect(sidebar.getByRole("button", { name: "Ouvrir Nouvelle conversation" })).toHaveCount(
    0,
  );
  await sidebar.getByRole("button", { name: "Ouvrir Révision des chaînes" }).click();
  await expect(page).toHaveURL(url);
  await expect(page.getByRole("heading", { name: "Bilan du training" })).toBeVisible();
  await expect(page.getByText("Leçons sélectionnées (1)", { exact: true })).toBeVisible();
  await search.clear();
  await page.screenshot({ path: testInfo.outputPath("training-conversations.png") });

  await sidebar.getByRole("button", { name: "Vider la conversation" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Confirmer" }).click();
  await expect(reply).toHaveCount(0);
  await expect(question).toBeEditable();
  await expect(mode).toHaveValue("direct");
  await expect(page.getByRole("heading", { name: "Bilan du training" })).toBeVisible();

  await sidebar.getByRole("button", { name: "Supprimer la conversation" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Confirmer" }).click();
  await expect(sidebar.getByRole("button", { name: "Ouvrir Révision des chaînes" })).toHaveCount(0);
  await sidebar.getByRole("button", { name: "Tout effacer" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Annuler" }).click();
  await expect(sidebar.getByRole("button", { name: "Ouvrir Nouvelle conversation" })).toBeVisible();
  await sidebar.getByRole("button", { name: "Tout effacer" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Confirmer" }).click();
  await expect(sidebar.getByText("Aucune conversation pour le moment.")).toBeVisible();
  await expect(
    sidebar.getByRole("button", { name: "Nouvelle conversation", exact: true }),
  ).toBeFocused();
});
