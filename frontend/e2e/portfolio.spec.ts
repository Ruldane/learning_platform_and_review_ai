import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_PORTFOLIO !== "1", "Utilise le stockage jetable de recette.");

test("sélectionne les faits, confirme l’adresse exacte et retire le site", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const profile = await request.put(`${API}/profile`, {
    data: {
      data: {
        identity: { name: "Mina Exemple", email: "interne@example.test" },
        summary: { text: "Présentation privée à écarter." },
      },
    },
  });
  expect(profile.ok()).toBe(true);
  await page.goto("/carriere/site-portfolio");
  await page.getByRole("checkbox", { name: "Nom affiché" }).check();
  await expect(page.getByRole("checkbox", { name: "Présentation", exact: true })).not.toBeChecked();
  await page.getByRole("button", { name: "Préparer l’aperçu" }).press("Enter");
  const frame = page.frameLocator('iframe[title="Aperçu privé du site"]');
  await expect(frame.getByRole("heading", { name: "Mina Exemple" })).toBeVisible();
  await expect(frame.getByText("Présentation privée à écarter.")).toHaveCount(0);
  await page.getByRole("button", { name: "Examiner la publication" }).press("Enter");
  await expect(
    page.getByRole("heading", { name: "Confirmer le contenu et la destination" }),
  ).toBeFocused();
  const url = await page
    .getByText(/^http:\/\/localhost:\d+\/api\/v1\/public\/portfolios\//)
    .textContent();
  if (!url) throw new Error("Adresse de recette absente.");
  expect((await request.get(url)).status()).toBe(404);
  await page.getByRole("button", { name: "Publier cette version" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Site publié" })).toBeFocused();
  const publicSite = await request.get(url);
  expect(publicSite.ok()).toBe(true);
  expect(await publicSite.text()).not.toContain("interne@example.test");
  await page.getByRole("button", { name: "Proposer le lien aux nouveaux CV" }).press("Enter");
  await expect(
    page.getByRole("button", { name: "Retirer la proposition pour les CV" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Retirer le site" }).press("Enter");
  await page.getByRole("button", { name: "Retirer cette version" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Site portfolio", exact: true })).toBeFocused();
  expect((await request.get(url)).status()).toBe(404);
});
