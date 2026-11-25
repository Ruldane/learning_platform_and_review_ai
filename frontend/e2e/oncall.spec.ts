import { expect, test, type Page } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

async function waitForAlert(page: Page): Promise<string> {
  const advance = page.getByRole("button", { name: "Avancer d’une minute" });
  for (let minute = 1; minute <= 4; minute += 1) {
    const [response] = await Promise.all([
      page.waitForResponse((result) => result.url().endsWith("/advance")),
      advance.click(),
    ]);
    expect(response.ok()).toBe(true);
    if ((await response.json()).alerted) return String(minute);
  }
  throw new Error("Le scénario devait déclencher une alerte.");
}

async function repairInEditor(page: Page): Promise<void> {
  await page.getByRole("link", { name: "Ouvrir le projet Python" }).click();
  await expect(page).toHaveURL(/\/code\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { name: "Astreinte · File de traitement" })).toBeVisible();
  await page.locator(".monaco-editor .view-lines").first().click();
  await page.keyboard.press("Control+Home");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Home");
  await page.keyboard.press("Shift+End");
  const saved = page.waitForResponse(
    (response) => response.request().method() === "PUT" && response.url().endsWith("/files"),
  );
  await page.keyboard.insertText("QUEUE_CAPACITY = 12");
  expect((await saved).ok()).toBe(true);
  await page.goBack();
}

test("l’astreinte lance l’alerte, rétablit le projet et conserve une preuve", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/on-call");
  await page.getByRole("combobox", { name: "Scénario" }).selectOption("queue");
  await page.getByRole("button", { name: "Démarrer un incident" }).click();
  await expect(page).toHaveURL(/\/on-call\/[0-9a-f-]+$/);
  const incident = page.url();
  await expect(page.getByText("En attente d’alerte")).toBeVisible();

  const alertMinute = await waitForAlert(page);
  await expect(page.getByRole("alert")).toHaveText("Alerte simulée");
  await page.getByRole("button", { name: `Consulter l’événement ${alertMinute}` }).click();
  await expect(
    page.getByRole("button", { name: `Événement ${alertMinute} consulté` }),
  ).toHaveAttribute("aria-pressed", "true");

  const diagnose = page.getByRole("button", { name: "Vérifier la réparation" });
  await diagnose.click();
  await expect(page.getByText("Le diagnostic a échoué.", { exact: false })).toBeVisible();
  await repairInEditor(page);
  await expect(page).toHaveURL(incident);
  await diagnose.click();
  await expect(page.getByText("Service rétabli")).toBeVisible();
  await page
    .getByRole("textbox", { name: "Rapport d’incident" })
    .fill(
      "La file de traitement saturait à deux requêtes. Une capacité adaptée a rétabli le service. " +
        "Le journal montre des requêtes en attente, et un contrôle de capacité préviendrait une récidive.",
    );
  await page.getByRole("button", { name: "Soumettre le rapport" }).click();
  const proof = page.getByText("Preuve ajoutée à la carte des compétences");
  await expect(proof).toBeVisible();
  await page.reload();
  await expect(proof).toBeVisible();
});
