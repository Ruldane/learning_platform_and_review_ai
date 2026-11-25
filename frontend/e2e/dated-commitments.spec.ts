import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_DATED_COMMITMENTS !== "1",
  "Utilise une horloge et des décisions fictives.",
);

test("retrouve après échéance le contexte et l’écart réellement mesuré", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/study/commitments");
  await page.getByLabel("Décision", { exact: true }).fill("Changer la cadence");
  await page.getByLabel("Version de la décision").fill("v2");
  await page.getByLabel("Intention", { exact: true }).fill("Réduire le temps d’une révision.");
  await page.getByLabel("Indicateur convenu").fill("Durée médiane");
  await page.getByLabel("Unité", { exact: true }).fill("min");
  await page.getByLabel("Valeur cible").fill("4,25");
  await page.getByLabel("Date du retour").fill("2030-01-08");
  await page.getByRole("button", { name: "Planifier l’engagement" }).press("Enter");
  await expect(page).toHaveURL(/\/study\/commitments\/[0-9a-f-]+$/);
  await expect(page.getByText("À venir", { exact: false })).toBeVisible();
  await expect(page.getByText("4,25 min", { exact: true })).toBeVisible();

  const tick = await request.post(new URL("/__e2e/dated-commitments/advance", API).toString());
  expect(tick.ok()).toBe(true);
  await page.reload();
  await expect(page.getByText("À revoir", { exact: false })).toBeVisible();
  await expect(page.getByText("Réduire le temps d’une révision.", { exact: true })).toBeVisible();
  await expect(page.getByText("v2", { exact: true })).toBeVisible();
  await page.getByLabel("Mesure observée").fill("3,5");
  await page.getByRole("button", { name: "Enregistrer la mesure" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Changer la cadence" })).toBeFocused();
  await expect(page.getByText(/^[-−]0,75 min$/)).toBeVisible();
  await page.reload();
  await expect(page.getByText("Mesure enregistrée", { exact: false })).toBeVisible();
  await expect(page.getByText(/^[-−]0,75 min$/)).toBeVisible();
});
