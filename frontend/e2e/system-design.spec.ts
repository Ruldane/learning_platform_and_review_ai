import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_SYSTEM_DESIGN !== "1", "Utilise le serveur de recette d’architecture.");

test("dessine, remet le dessin enregistré et relit la critique", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/candidatures/entretien");
  await page.getByRole("link", { name: "Entraînement system design" }).press("Enter");
  await page.getByRole("button", { name: "Ouvrir un sujet d’architecture" }).press("Enter");
  await expect(
    page.getByRole("heading", { name: "Concevoir un service de rappels" }),
  ).toBeVisible();
  const rectangle = page.getByRole("radio", { name: "Rectangle", exact: true });
  await page.locator("label").filter({ has: rectangle }).click({ timeout: 30000 });
  await expect(rectangle).toBeChecked();
  const canvas = page.locator("canvas.excalidraw__canvas.interactive").first();
  await canvas.scrollIntoViewIfNeeded();
  const bounds = await canvas.boundingBox();
  if (!bounds) throw new Error("Le tableau d’architecture ne s’est pas affiché.");
  await page.mouse.move(bounds.x + bounds.width * 0.4, bounds.y + bounds.height * 0.45);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * 0.58, bounds.y + bounds.height * 0.65, {
    steps: 10,
  });
  await page.mouse.up();
  await page.getByRole("button", { name: "Enregistrer le dessin" }).press("Enter");
  await expect(page.getByText("Version enregistrée · 1")).toBeVisible();
  await page
    .getByRole("textbox", { name: "Défends tes choix d’architecture" })
    .fill("Une file absorbe les pointes. Une clé d’idempotence empêche l’envoi en double.");
  await page.getByRole("button", { name: "Remettre la version enregistrée" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Critique d’architecture" })).toBeFocused();
  await expect(page.getByText("Version remise · 1")).toBeVisible();
  await expect(page.getByText("Preuve ajoutée à ta carte des compétences.")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Version remise · 1")).toBeVisible();
});
