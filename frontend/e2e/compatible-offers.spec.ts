import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_COMPATIBLE_OFFERS !== "1",
  "Requiert le serveur synthétique tests.e2e.compatible_offers.",
);

test("ouvre l’écart depuis le brief et propose la compétence cochée", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/");
  await page.getByRole("link", { name: /Voir l’écart · Ingénieure recherche documentaire/ }).press("Enter");
  await expect(page.getByRole("heading", { name: "Ingénieure recherche documentaire" })).toBeVisible();
  const checkbox = page.getByRole("checkbox", { name: /Recherche hybride/ });
  await checkbox.press("Space");
  await expect(checkbox).toBeChecked();
  await page.getByRole("button", { name: "Proposer l’ajout au planning" }).press("Enter");
  await expect(page.getByRole("link", { name: "Ouvrir la proposition de replanification" }))
    .toHaveAttribute("href", /\/apprendre\/programme\/[0-9a-f-]+\/replanification$/);
});
