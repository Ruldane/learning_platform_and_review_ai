import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_MOBILE_REVIEWS !== "1",
  "Requiert le build de production et le serveur synthétique tests.e2e.mobile_reviews.",
);

test("démarre hors ligne, enregistre une réponse et la synchronise", async ({ page, context, request }) => {
  await finishFirstLaunch(request);
  let agendaReads = 0;
  await page.route("**/api/v1/calendar/upcoming", async (route) => {
    agendaReads += 1;
    await route.fulfill({ json: {
      id: "rappel-de-recette",
      kind: "study",
      start: new Date(Date.now() + 10 * 60_000).toISOString(),
      end: new Date(Date.now() + 30 * 60_000).toISOString(),
      timezone: "Europe/Paris",
    } });
  });
  await page.addInitScript(() => {
    Object.defineProperty(Notification, "permission", { configurable: true, value: "default" });
    Notification.requestPermission = () => {
      Object.defineProperty(Notification, "permission", { configurable: true, value: "granted" });
      return Promise.resolve("granted");
    };
    ServiceWorkerRegistration.prototype.showNotification = () => Promise.resolve();
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/mobile");
  await expect(page.getByRole("heading", { name: "Ton brief du jour" })).toBeVisible();
  await page.getByRole("button", { name: "Garder le brief et les fiches sur cet appareil" }).press("Enter");
  await expect(page.getByText("Brief et fiches sauvegardés sur cet appareil.")).toBeVisible();
  await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);
  expect(agendaReads).toBe(0);
  await page.getByRole("button", { name: "Autoriser les notifications" }).press("Enter");
  await expect.poll(() => page.evaluate(() =>
    localStorage.getItem("tremplin:mobile:notification:agenda"))).toContain("rappel-de-recette");
  expect(agendaReads).toBe(1);

  await context.setOffline(true);
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByText("Hors connexion", { exact: true })).toBeVisible();
  await expect(page.getByText("Quel outil traite ce jeu de données fictif ?")).toBeVisible();
  await page.getByRole("button", { name: "Voir la réponse" }).press("Enter");
  await page.getByRole("button", { name: "Réussie" }).press("Enter");
  await expect(page.getByText(/1 réponse\(s\) à synchroniser/)).toBeVisible();

  await context.setOffline(false);
  await expect(page.getByText(/1 réponse\(s\) synchronisée\(s\)/)).toBeVisible();
  await expect(page.getByText("Aucune autre fiche à réviser.")).toBeVisible();
  await page.getByRole("button", { name: "Effacer les données hors connexion" }).press("Enter");
  const copied = await page.evaluate(() =>
    Object.keys(localStorage).filter((key) => key.startsWith("tremplin:mobile:")));
  expect(copied).toEqual([]);
});
