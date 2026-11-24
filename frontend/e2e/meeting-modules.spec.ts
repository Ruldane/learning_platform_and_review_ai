import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_MEETING_MODULES !== "1", "Requiert la base locale de recette.");

test("compose un module à partir de deux lignes choisies puis le range", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/study/meeting-modules");
  await page.getByLabel("Titre du module").fill("Préparer l’atelier de juillet");
  await page
    .getByLabel("Extrait de la réunion")
    .fill(
      [
        "Vendredi matin.",
        "Nous avons décidé de garder le stock tampon à l’atelier.",
        "À étudier : Comparer deux seuils de réapprovisionnement.",
      ].join("\n"),
    );
  await page.getByRole("button", { name: "Repérer les extraits" }).click();
  await page.getByRole("checkbox", { name: /garder le stock tampon/ }).check();
  await page.getByRole("checkbox", { name: /Comparer deux seuils/ }).check();
  await expect(page.getByRole("button", { name: "Ranger ce module" })).toHaveCount(0);
  await page.getByRole("button", { name: "Prévisualiser la séquence" }).click();
  await expect(page.getByRole("heading", { name: "Séquence d’étude" })).toBeVisible();
  await page.getByRole("button", { name: "Ranger ce module" }).click();
  await expect(page.getByText("Module rangé", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Nous avons décidé de garder le stock tampon à l’atelier.")).toBeVisible();
  await expect(page.getByText(/Reformule la décision et compare-la/)).toBeVisible();
  await expect(page.getByText("Comparer deux seuils de réapprovisionnement.")).toBeVisible();
  await expect(page.getByRole("checkbox")).toHaveCount(0);
});
