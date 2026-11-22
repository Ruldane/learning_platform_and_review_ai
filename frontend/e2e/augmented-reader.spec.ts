import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_AUGMENTED_READER !== "1",
  "Requiert le serveur synthétique tests.e2e.augmented_reader.",
);

test("ouvre une définition au clavier et crée une fiche du passage choisi", async ({ page, request }) => {
  const passage = "Le terme mène à une liste de documents.";
  await finishFirstLaunch(request);
  await page.goto("/memoire/lecture");
  await page.getByRole("link", { name: "Comprendre les index" }).click();
  const term = page.getByRole("button", { name: "index inversé", exact: true });
  await term.focus();
  const definition = page.getByRole("complementary", { name: "Définition de Index inversé" });
  await expect(definition).toContainText("Un index qui associe un terme aux documents");
  await term.press("Enter");
  await expect(definition).toBeFocused();
  await page.keyboard.press("Tab");
  const chapter = definition.getByRole("link", { name: /Chapitre/ });
  await expect(chapter).toBeFocused();
  await expect(chapter).toHaveAttribute("href", /\/apprendre\/lecons\/[0-9a-f-]+$/);

  await term.evaluate((button, selected) => {
    const text = button.parentNode?.lastChild;
    const content = text?.textContent ?? "";
    const start = content.indexOf(selected);
    if (!text || start < 0) throw new Error("Passage absent de la lecture.");
    const range = document.createRange();
    range.setStart(text, start);
    range.setEnd(text, start + selected.length);
    const selection = document.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
  }, passage);
  const saved = page.waitForResponse((response) => response.url().endsWith("/cards"));
  await page.getByRole("button", { name: "Créer une fiche de ce passage" }).click();
  expect((await saved).request().postDataJSON()).toEqual({ passage });
  await expect(page.getByText("La fiche est prête à réviser.")).toBeVisible();
});
