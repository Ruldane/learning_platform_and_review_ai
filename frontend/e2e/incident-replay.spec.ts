import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_INCIDENT_REPLAY !== "1", "Requiert la base locale de recette.");

test("revient au premier signal et retrouve la décision proposée", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/etudier/replay-incident");
  await page
    .getByRole("region", { name: "File d’attente en surcharge" })
    .getByRole("button", { name: "Rejouer cet incident" })
    .click();
  const timeline = page.getByRole("slider", { name: "Position dans la chronologie" });
  await expect(timeline).toHaveAttribute("aria-valuetext", "Minute 0");
  await timeline.press("End");
  await expect(page.getByText("Les reprises sont espacées")).toBeVisible();
  await timeline.press("Home");
  await timeline.press("ArrowRight");
  await expect(timeline).toHaveAttribute("aria-valuetext", "Minute 4");
  await expect(page.getByText("Les reprises sont espacées")).toHaveCount(0);
  await page
    .getByLabel("Autre décision possible")
    .fill("Examiner le taux de reprise avant d’ajouter des processus.");
  await page.getByRole("button", { name: "Consigner l’hypothèse" }).click();
  await expect(page.getByText("Hypothèse enregistrée.", { exact: true })).toBeVisible();
  await page.reload();
  await expect(timeline).toHaveAttribute("aria-valuetext", "Minute 4");
  await expect(
    page.getByText("Examiner le taux de reprise avant d’ajouter des processus."),
  ).toBeVisible();
});
