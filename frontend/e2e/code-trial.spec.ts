import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_CODE_TRIAL !== "1",
  "Requiert le serveur synthétique tests.e2e.code_trial.",
);

test("compare les plaidoiries du projet et retrouve le verdict à la reprise", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const created = await request.post(`${API}/ide/sessions`, { data: { title: "Projet fictif" } });
  expect(created.status()).toBe(201);
  const session = (await created.json()) as { id: string };
  const files = {
    "main.py": "from rules import total\n\nprint(total([1, 2]))\n",
    "rules.py": "def total(values):\n    return sum(values)\n",
  };
  const saved = await request.put(`${API}/ide/sessions/${session.id}/files`, { data: { files } });
  expect(saved.status()).toBe(200);
  await page.goto(`/code/${session.id}`);
  await page.getByRole("link", { name: "Procès de ton code" }).click();
  await page.getByRole("button", { name: "Ouvrir le procès" }).click();

  const prosecution = page.getByRole("region", { name: "Procureur" });
  const defense = page.getByRole("region", { name: "Avocat" });
  await expect(prosecution.getByText(/se teste difficilement/)).toBeVisible();
  await expect(defense.getByText("Le calcul reste séparé de la présentation.")).toBeVisible();
  await defense.getByText("rules.py · lignes 1 à 2", { exact: true }).click();
  await expect(defense.getByText(/return sum\(values\)/)).toBeVisible();

  const reason = "Je garde le calcul séparé et j’isole la présentation.";
  await page.getByRole("combobox", { name: "Décision" }).selectOption("compromise");
  await page.getByRole("textbox", { name: "Motif du verdict" }).fill(reason);
  await page.getByRole("button", { name: "Enregistrer mon verdict" }).click();
  await expect(page.getByRole("heading", { name: "Verdict enregistré" })).toBeFocused();
  await page.reload();
  await expect(page.getByText(reason)).toBeVisible();
  const current = await request.get(`${API}/ide/sessions/${session.id}`);
  expect(((await current.json()) as { files: typeof files }).files).toEqual(files);
});
