import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_ROUTINES !== "1", "Requiert le planificateur local de recette.");

test("la routine s’exécute à l’heure et reste suspendue après rechargement", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/settings/routines");
  await page.getByLabel("Heure du rappel").fill("08:45");
  await page.getByRole("button", { name: "Activer la routine" }).press("Enter");
  await expect(page.getByText("Routine active.")).toBeVisible();
  await expect(page.getByText("Planifiée", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Fiches à revoir · 0")).toBeVisible();
  await page.getByRole("button", { name: "Exécuter maintenant" }).press("Enter");
  await expect(page.getByText("Manuelle", { exact: true })).toHaveCount(1);
  await page.getByRole("button", { name: "Suspendre la routine" }).press("Enter");
  await page.reload();
  await expect(page.getByText("Routine suspendue.")).toBeVisible();
  await expect(page.getByText("Planifiée", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Manuelle", { exact: true })).toHaveCount(1);

  const owned = (await (await request.get(`${API}/routines`)).json()) as { id: string }[];
  const rule = owned[0];
  if (!rule) throw new Error("Routine de recette introuvable.");
  const changed = await request.patch(`${API}/routines/${rule.id}`, {
    data: { local_time: "09:15" },
  });
  expect(changed.ok()).toBe(true);
  await expect(page.getByLabel("Heure du rappel")).toHaveValue("09:15", { timeout: 12_000 });
});
