import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_PROOF_PACKETS !== "1", "Requiert une mission synthétique approuvée.");

const ARTIFACT = "Résultats observés sur les deux cas du prototype fictif.";
const PACKET = "Preuves du prototype mesuré";

async function approveMission(request: APIRequestContext) {
  const offers = await request.get(`${API}/postings`);
  expect(offers.ok()).toBe(true);
  const [choice]: { id: string }[] = await offers.json();
  if (!choice) throw new Error("Offre de recette absente.");
  const created = await request.post(`${API}/missions`, {
    data: { posting_id: choice.id, requirement_indices: [0] },
  });
  expect(created.status()).toBe(201);
  const { id } = await created.json();
  const path = `${API}/missions/${id}`;
  expect((await request.patch(`${path}/criteria/0`, {
    data: { revision: 0, observed: 2 },
  })).ok()).toBe(true);
  const submitted = await request.post(`${path}/submission`, {
    data: { revision: 1, artifact: ARTIFACT },
  });
  expect(submitted.ok()).toBe(true);
  return submitted.json();
}

test("constitue, relit et exporte un manifeste privé", async ({ page, request }) => {
  await finishFirstLaunch(request);
  const mission = await approveMission(request);
  await page.goto("/career/evidence");
  await page.getByLabel("Nom du dossier").fill(PACKET);
  await page.getByRole("checkbox", { name: /Ingénierie des données/ }).check();
  await page.getByRole("button", { name: "Prévisualiser", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Aperçu du manifeste" })).toBeVisible();
  await expect(page.getByText(ARTIFACT)).toBeVisible();
  await page.getByRole("button", { name: "Enregistrer le dossier" }).click();
  await expect(page.getByText("Dossier enregistré.")).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: new RegExp(PACKET) }).click();
  await expect(page.getByText(ARTIFACT)).toBeVisible();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exporter le manifeste JSON" }).click();
  const result = await downloaded;
  expect(result.suggestedFilename()).toBe("dossier-de-preuves.json");
  const path = await result.path();
  const bytes = await readFile(path);
  const manifest = JSON.parse(bytes.toString("utf-8"));
  expect(manifest.proofs[0]).toMatchObject({
    proof_id: mission.submission.proof_id,
    revision: mission.revision,
    artifact: ARTIFACT,
  });
  const digest = createHash("sha256").update(bytes).digest("hex");
  await expect(page.getByText(digest, { exact: true })).toBeVisible();
});
