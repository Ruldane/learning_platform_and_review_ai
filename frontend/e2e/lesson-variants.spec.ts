import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_LESSON_VARIANTS !== "1", "Requiert une leçon fictive publiée côté serveur.");

test("compare deux lectures et retrouve la version source", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/apprendre/variantes");
  await page.getByRole("combobox", { name: "Programme" }).selectOption({ index: 1 });
  await page.getByRole("combobox", { name: "Leçon publiée" }).selectOption({ label: "Index et recherche" });
  await page.getByRole("button", { name: "Préparer les variantes" }).click();
  const formats = page.getByRole("combobox", { name: "Format de lecture" });
  await expect(formats).toHaveValue("review");
  const reference = page.getByRole("link", { name: "Documentation de l’index" });
  await expect(reference).toHaveAttribute("href", "https://example.org/index");
  const headings = page.getByRole("heading", { level: 2 });
  expect((await headings.allTextContents()).indexOf("Exemple travaillé"))
    .toBeLessThan((await headings.allTextContents()).indexOf("Explication"));
  const revision = await page.getByText(/^[a-f0-9]{64}$/).textContent();
  if (!revision) throw new Error("La recette attend une révision source.");
  expect(revision).toMatch(/^[a-f0-9]{64}$/);

  await formats.selectOption("guided");
  await expect(page.getByRole("heading", { name: "Étapes de lecture" })).toBeVisible();
  await expect(page.getByText("Reconnaître le rôle d’un index.")).toBeVisible();
  await expect(reference).toHaveAttribute("href", "https://example.org/index");
  expect((await headings.allTextContents()).indexOf("Explication"))
    .toBeLessThan((await headings.allTextContents()).indexOf("Exemple travaillé"));

  await formats.selectOption("source");
  await page.reload();
  await expect(formats).toHaveValue("source");
  await expect(page.getByText(revision)).toBeVisible();
  await expect(reference).toBeVisible();
});
