import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test("retrouve au clavier le notebook et ses onglets après réouverture", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const made = await request.post(`${API}/ide/sessions`, {
    data: { title: "Projet Python fictif" },
  });
  expect(made.ok()).toBe(true);
  const { id } = (await made.json()) as { id: string };
  await page.goto(`/code/${id}`);

  await page.getByRole("button", { name: "Nouveau fichier" }).press("Enter");
  const filename = page.getByRole("textbox", { name: "Chemin du fichier" });
  await expect(filename).toBeFocused();
  await filename.fill("notes/essai.ipynb");
  await filename.press("Enter");

  await page.getByRole("button", { name: "Ajouter une cellule Python" }).press("Enter");
  const source = page.getByRole("textbox", { name: "Source de la cellule 1" });
  await source.fill("print('données fictives')");
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().endsWith("/notebook") &&
        response.request().method() === "PUT" &&
        response.ok(),
    ),
    page.getByRole("button", { name: "Enregistrer le notebook" }).press("Enter"),
  ]);

  await page.reload();
  await expect(source).toHaveValue("print('données fictives')");
  const tabs = page.getByRole("navigation", { name: "Fichiers de la séance" });
  await expect(
    tabs.getByRole("button", { name: "notes/essai.ipynb", exact: true }),
  ).toHaveAttribute("aria-current", "true");
  await tabs
    .getByRole("button", { name: "Fermer l’onglet notes/essai.ipynb", exact: true })
    .press("Enter");
  await expect(tabs.getByRole("button", { name: /^main\.py/ })).toBeFocused();
});
