import { expect, test, type APIRequestContext } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

async function createProject(request: APIRequestContext): Promise<string> {
  await finishFirstLaunch(request);
  const made = await request.post(`${API}/ide/sessions`, {
    data: { title: "Projet Python fictif" },
  });
  expect(made.ok()).toBe(true);
  const { id } = (await made.json()) as { id: string };
  return id;
}

test("retrouve au clavier le notebook et ses onglets après réouverture", async ({
  page,
  request,
}) => {
  const id = await createProject(request);
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

test("pilote le terminal au clavier et revient au fichier indiqué par le Professeur", async ({
  page,
  request,
}) => {
  const id = await createProject(request);
  const seeded = await request.put(`${API}/ide/sessions/${id}/files`, {
    data: { files: { "main.py": "print('bonjour')\n", "outils.py": "# Autre fichier\n" } },
  });
  expect(seeded.ok()).toBe(true);
  await page.goto(`/code/${id}`);

  const open = page.getByRole("button", { name: "Ouvrir le terminal" });
  await open.press("Enter");
  const input = page.getByRole("textbox", { name: "Entrée du terminal" });
  await expect(input).toBeFocused();
  await input.fill("echo tremplin-recette");
  await input.press("Enter");
  await expect(page.getByRole("log", { name: "Sortie du terminal" })).toHaveText("tremplin-recette");
  await page.getByRole("button", { name: "Interrompre le terminal" }).press("Enter");
  await expect(page.getByText("Terminal fermé", { exact: true })).toBeVisible();
  await expect(open).toBeFocused();

  const teacher = page.getByRole("region", { name: "Professeur", exact: true });
  const question = teacher.getByRole("textbox", { name: "Ta question" });
  await question.fill("Que fait la première ligne de main.py ?");
  await question.press("Enter");
  const note = teacher
    .getByRole("listitem")
    .filter({ hasText: "Relis le premier appel dans ce fichier." });
  await expect(note).toBeVisible();

  const tree = page.getByRole("navigation", { name: "Fichiers du projet" });
  const other = tree.getByRole("button", { name: "outils.py", exact: true });
  await other.press("Enter");
  await expect(other).toHaveAttribute("aria-current", "true");
  await note.getByRole("button", { name: "Ouvrir main.py" }).press("Enter");
  await expect(tree.getByRole("button", { name: "main.py", exact: true })).toHaveAttribute(
    "aria-current",
    "true",
  );
});
