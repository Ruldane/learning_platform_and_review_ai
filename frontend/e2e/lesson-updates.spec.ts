import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_LESSON_UPDATES !== "1", "Requiert tests.e2e.lesson_updates.");

test("compare une correction de version puis la soumet à la publication", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/apprendre/lecons");
  await page.getByRole("link", { name: "Lire « Module Bases »", exact: true }).click();
  const updates = page.getByRole("region", { name: "Veille des versions" });
  const proposal = updates.getByRole("article", { name: "fictilib 2.0.0" });
  await expect(proposal).toHaveCount(1);
  await expect(proposal.getByText("Correction à valider")).toBeVisible();
  await expect(
    proposal.getByRole("link", { name: "Consulter le journal de versions" }),
  ).toBeVisible();

  await proposal.getByText("Comparer l’exemple 1").click();
  await expect(proposal.locator("pre").filter({ hasText: /lib\.old_api/ })).toBeVisible();
  await expect(proposal.locator("pre").filter({ hasText: /lib\.new_api/ })).toBeVisible();
  await expect(page.locator("pre").filter({ hasText: /lib.old_api/ })).toHaveCount(2);
  await proposal.getByRole("button", { name: "Approuver et vérifier la correction" }).click();

  await expect(proposal.getByText("Correction publiée")).toBeVisible({ timeout: 30000 });
  await expect(page.locator("pre").filter({ hasText: /lib.new_api/ })).toHaveCount(2);
  await expect(page.locator("pre").filter({ hasText: /lib.old_api/ })).toHaveCount(1);
  await page.reload();
  await expect(proposal.getByText("Correction publiée")).toBeVisible();
});
