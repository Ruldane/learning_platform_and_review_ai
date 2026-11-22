import { createHash } from "node:crypto";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

async function uploadNotes(request: APIRequestContext) {
  const started = await request.post(`${API}/brain/folders`, {
    data: { name: "Galaxie fictive", path: "C:/fictif/galaxie" },
  });
  expect(started.status()).toBe(201);
  const { id, revision } = (await started.json()) as { id: string; revision: number };
  const token = await request.post(`${API}/brain/sync-token`);
  expect(token.ok()).toBe(true);
  const { token: credential } = (await token.json()) as { token: string };
  const docs = [
    ["depart.md", "# Note de départ\n\nUne note générée qui cite [[Note d’arrivée]]."],
    ["arrivee.md", "# Note d’arrivée\n\nUne autre note fictive pour la recette."],
  ] as const;
  for (const [path, markdown] of docs) {
    const buffer = Buffer.from(markdown);
    const added = await request.post(`${API}/brain/sync/folders/${id}/files`, {
      headers: {
        Authorization: `Bearer ${credential}`,
        "X-Tremplin-Folder-Revision": String(revision),
      },
      multipart: {
        path,
        sha256: createHash("sha256").update(buffer).digest("hex"),
        file: { name: path, mimeType: "text/markdown", buffer },
      },
    });
    expect(added.status()).toBe(202);
  }
}

async function rotateAndZoom(page: Page) {
  const canvas = page.locator("canvas");
  const image = await canvas.evaluate((element: HTMLCanvasElement) => element.toDataURL());
  await page.getByRole("button", { name: "Pivoter à droite" }).press("Enter");
  await expect
    .poll(async () =>
      canvas.evaluate((el: HTMLCanvasElement, before) => el.toDataURL() !== before, image),
    )
    .toBe(true);
  const zoom = page.getByRole("slider", { name: "Zoom de la galaxie" });
  await zoom.press("ArrowRight");
  await expect(zoom).toHaveValue("1.05");
}

test("la Galaxie projette les nœuds et les ouvre aussi au clavier", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/competences/galaxie");
  await expect(page.getByText("Aucune compétence ni note active à afficher.")).toBeVisible();
  expect((await request.post(`${API}/skills`, { data: { name: "Python fictif" } })).status()).toBe(
    201,
  );
  await uploadNotes(request);
  await expect
    .poll(async () => {
      const graph = await request.get(`${API}/galaxy`);
      const data = (await graph.json()) as { edges: { kind: string }[] };
      return data.edges.some((edge) => edge.kind === "reference");
    })
    .toBe(true);

  await page.reload();
  await rotateAndZoom(page);
  const departure = page.getByRole("button", {
    name: "Note de départ Note du Cerveau",
    exact: true,
  });
  await departure.press("Enter");
  await expect(departure).toHaveAttribute("aria-pressed", "true");
  const selected = page.getByRole("region", { name: "Notion sélectionnée" });
  await selected.getByRole("button", { name: "Note d’arrivée", exact: true }).press("Enter");
  await expect(
    page.getByRole("button", { name: "Note d’arrivée Note du Cerveau", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Python fictif Compétence", exact: true }).press("Enter");
  await selected.getByRole("link", { name: "Ouvrir l’entraînement" }).click();
  await expect(page).toHaveURL(/\/etudier\/training\?competence=[0-9a-f-]+$/);
  await expect(page.getByText("Sujet proposé · Python fictif")).toBeVisible();
  await page.getByRole("button", { name: "Commencer le training" }).click();
  await expect(page.getByRole("textbox", { name: "Ton message au tuteur" })).toHaveValue(
    "J’aimerais m’entraîner sur Python fictif.",
  );
});
