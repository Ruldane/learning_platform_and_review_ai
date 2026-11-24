import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_CONCENTRATION !== "1", "Requiert le serveur synthétique du Pilote.");

test("accepte une pause après plusieurs erreurs et reprend le même training", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/study/training", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Commencer le training" }).click();
  await expect(page).toHaveURL(/\/study\/training\/[0-9a-f-]+$/);
  const url = page.url();
  await page.clock.install();
  const input = page.getByRole("textbox", { name: "Ton message au tuteur" });
  const finish = page.getByRole("button", { name: "Terminer le training" });
  for (let index = 0; index <= 6; index += 1) {
    await expect(finish).toBeEnabled();
    await input.fill(`Réponse synthétique ${index}.`);
    await page.clock.fastForward(index < 4 ? 1_000 : 12_000);
    await input.press("Enter");
    await expect(
      page.getByText(index === 0 ? "Première question du tuteur." : `Réponse du tuteur ${index}.`, {
        exact: true,
      }),
    ).toBeVisible();
    await expect(finish).toBeEnabled();
    if (index < 6)
      await expect(page.getByRole("heading", { name: "Pilote de concentration" })).toHaveCount(0);
  }

  await expect(page.getByRole("heading", { name: "Pilote de concentration" })).toBeVisible();
  await input.fill("Brouillon à retrouver après la pause.");
  await page.getByRole("button", { name: "Faire une pause" }).press("Enter");
  const paused = page.getByRole("heading", { name: "Pause en cours" });
  await expect(paused).toBeFocused();
  await expect(input).toBeHidden();
  await page.clock.fastForward(45_000);
  await page.getByRole("button", { name: "Reprendre au même endroit" }).press("Enter");
  await expect(page).toHaveURL(url);
  await expect(input).toHaveValue("Brouillon à retrouver après la pause.");
  await expect(input).toBeFocused();
  await expect(page.getByText("Réponse du tuteur 6.", { exact: true })).toBeVisible();
});
