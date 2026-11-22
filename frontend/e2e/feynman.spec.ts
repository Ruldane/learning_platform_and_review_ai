import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_FEYNMAN !== "1", "Utilise le serveur synthétique Feynman.");

test("explique le fichier enregistré, reprend la relance et garde le bilan", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const created = await request.post(`${API}/ide/sessions`, { data: { title: "Somme d’exemple" } });
  expect(created.ok()).toBe(true);
  const session = (await created.json()) as { id: string };
  const saved = await request.put(`${API}/ide/sessions/${session.id}/files`, {
    data: { files: { "main.py": "def total(values):\n    return sum(values)\n" } },
  });
  expect(saved.ok()).toBe(true);
  await page.goto(`/code/${session.id}`);
  await page.getByRole("button", { name: "Explique-moi" }).press("Enter");
  await expect(page.getByText("Fichier à expliquer · main.py")).toBeVisible();
  await page.getByRole("button", { name: "Commencer l’explication" }).press("Enter");
  const explanation = page.getByRole("textbox", { name: "Ton explication" });
  await explanation.fill("La fonction additionne les valeurs de la liste.");
  await page.getByRole("button", { name: "Répondre" }).press("Enter");
  await expect(page.getByText("Que renvoie la fonction si la liste est vide ?")).toBeVisible();
  await page.reload();
  await explanation.fill("Une liste vide donne zéro, l’élément neutre de la somme.");
  await page.getByRole("button", { name: "Répondre" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Bilan de l’explication" })).toBeFocused();
  await expect(page.getByText("Quelle somme pour une liste vide ?")).toBeVisible();
  await page.getByRole("button", { name: "Garder les propositions" }).press("Enter");
  await expect(page.getByText("Propositions enregistrées.")).toBeFocused();
  await page.reload();
  await expect(page.getByText("Propositions enregistrées.")).toBeVisible();
});
