import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_FUTURE_SELF !== "1",
  "Requiert le serveur synthétique tests.e2e.future_self.",
);

test("compare une autre disponibilité et ouvre le chapitre classé au clavier", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/career/future-self");
  await expect(page.getByRole("heading", { name: "Ton futur toi" })).toBeVisible();
  const observed = page.getByRole("region", { name: "Rythme observé" });
  await expect(observed.getByText("2 h par semaine")).toBeVisible();
  await expect(observed.getByText("lundi 23 novembre")).toBeVisible();
  await expect(page.getByRole("note")).toContainText("Moins de 30 offres exploitables.");

  const role = page.getByRole("textbox", { name: "Poste visé" });
  const zone = page.getByRole("textbox", { name: "Zone du radar" });
  const hours = page.getByRole("spinbutton", { name: "Heures par semaine à simuler" });
  await role.focus();
  await page.keyboard.press("Tab");
  await expect(zone).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(hours).toBeFocused();
  await page.keyboard.type("4");
  await page.keyboard.press("Enter");
  const alternative = page.getByRole("region", { name: "Disponibilité simulée" });
  await expect(alternative.getByText("vendredi 20 novembre")).toBeVisible();
  await expect(alternative.getByText("75 %")).toBeVisible();
  await expect(page.getByRole("link", { name: "Proposer une replanification" })).toHaveAttribute(
    "href",
    /\/learn\/programs\/[0-9a-f-]+\/replan$/,
  );

  const chapter = page.getByRole("link", { name: "Recherche augmentée" });
  for (
    let step = 0;
    step < 6 && !(await chapter.evaluate((a) => a === document.activeElement));
    step += 1
  ) {
    await page.keyboard.press("Tab");
  }
  await expect(chapter).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/learn\/lessons\/[0-9a-f-]+$/);
  await expect(page.getByText("Chapitre synthétique.")).toBeVisible();
});
