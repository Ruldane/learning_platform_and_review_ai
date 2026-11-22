import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_SALARY_NEGOTIATION !== "1",
  "Requiert le serveur synthétique tests.e2e.salary_negotiation.",
);

test("négocie dans la fourchette du relevé et retrouve la marge au bilan", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/candidatures/entretien");
  await page.getByRole("textbox", { name: "Intitulé du poste" }).fill("Ingénieure IA");
  await page.getByRole("radio", { name: "Négociation de salaire" }).check();
  await page.getByRole("radio", { name: "15 minutes" }).check();
  await page.getByRole("textbox", { name: "Zone du relevé" }).fill("Lyon");
  await page.getByRole("button", { name: "Commencer l'entretien", exact: true }).click();

  const source = page.getByRole("region", { name: "Données du radar" });
  await expect(source).toContainText("50 000 € à 70 000 € bruts par an");
  await expect(source.getByRole("link", { name: "Consulter le relevé" })).toHaveAttribute(
    "href",
    /\/carriere\/radar\/[0-9a-f-]+$/,
  );
  await expect(page.getByRole("region", { name: "Règles de la simulation" })).toBeVisible();
  const answer = page.getByRole("textbox", { name: "Ta réponse écrite" });
  await answer.fill("Je demande une révision du fixe pour assurer le support du service.");
  await answer.press("Control+Enter");
  const thread = page.getByRole("list", { name: "Fil du débat" });
  await expect(thread.getByText(/je peux porter l’offre à 70 000 €/)).toBeVisible();
  await page.getByRole("button", { name: "Terminer l'entretien" }).click();

  const outcome = page.getByRole("region", { name: "Bilan de la simulation" });
  await expect(outcome).toContainText("70 000 €");
  await expect(outcome).toContainText("Marge restante dans la simulation : 0 € bruts par an.");
  await expect(page.getByText("99 000 €", { exact: false })).toHaveCount(0);
});
