import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_VOICE_FIXTURES !== "1", "Utilise le micro et les fournisseurs fictifs.");
test.use({
  launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] },
});

const corrected = "Je structure ma réponse avec le contexte, l’action et le résultat.";

test("écoute la question, corrige le brouillon audio et ouvre le débrief", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/applications/interview");
  await page.getByRole("textbox", { name: "Intitulé du poste" }).fill("Développeuse Python");
  await page.getByRole("radio", { name: "Technique", exact: true }).check();
  await page.getByRole("radio", { name: "15 minutes" }).check();
  await page.getByRole("button", { name: "Commencer l'entretien", exact: true }).click();

  await page.getByRole("button", { name: "Préparer la lecture par une voix IA" }).press("Enter");
  await expect(page.locator("audio")).toBeVisible();
  await page.getByRole("button", { name: "Annuler l’audio" }).press("Enter");

  const answer = page.getByRole("textbox", { name: "Ta réponse écrite" });
  await expect(answer).toHaveValue("");
  await page.getByRole("button", { name: "Démarrer l’enregistrement" }).press("Enter");
  const stop = page.getByRole("button", { name: "Arrêter l’enregistrement" });
  await expect(stop).toBeEnabled();
  await stop.press("Enter");
  await page.getByRole("button", { name: "Transcrire l’enregistrement" }).press("Enter");
  await expect(answer).toHaveValue("Une explication dictée à vérifier.");
  await answer.fill(corrected);
  await answer.press("Control+Enter");
  await page.getByRole("button", { name: "Terminer l'entretien" }).click();
  await expect(page.getByRole("heading", { name: "Débrief de l'entretien" })).toBeVisible();
  await expect(page.getByText("Clarté", { exact: true })).toBeVisible();
  await expect(page.getByText("Structure", { exact: true })).toBeVisible();
});
