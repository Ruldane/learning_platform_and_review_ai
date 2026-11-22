import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_LINKEDIN_DRAFTS !== "1",
  "Requiert le serveur synthétique tests.e2e.linkedin_drafts.",
);

test("corrige le résumé proposé et peut ensuite le copier", async ({ page, request }) => {
  const corrected = "Je développe des scripts Python.";
  await finishFirstLaunch(request);
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      value: {
        async write([item]: ClipboardItem[]) {
          const blob = await item!.getType("text/plain");
          document.body.dataset.copiedSummary = await blob.text();
        },
      },
    });
  });
  await page.goto("/carriere/linkedin");
  await page.getByRole("button", { name: "Préparer les propositions" }).press("Enter");
  await expect(page.getByText("Résumé · 900")).toBeVisible();
  const copy = page.getByRole("button", { name: "Copier le résumé" });
  await expect(copy).toBeDisabled();
  await page.getByRole("textbox", { name: "Résumé", exact: true }).fill(corrected);
  await page.getByRole("button", { name: "Enregistrer et vérifier" }).press("Enter");
  await expect(copy).toBeEnabled();
  await copy.press("Enter");
  await expect(page.locator("body")).toHaveAttribute("data-copied-summary", corrected);
  await expect(page.getByRole("status").filter({ hasText: "Texte copié." })).toBeVisible();
});
