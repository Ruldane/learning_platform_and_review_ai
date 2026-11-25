import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_SKILL_TRANSFER !== "1", "Requiert le Vérificateur synthétique.");

test("programme, résout et retrouve un contrôle de transfert pour une compétence", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const seeded = await request.post(`${new URL(API).origin}/e2e/skill-transfer/ready`);
  expect(seeded.ok()).toBe(true);
  const { skill_id: skillId } = (await seeded.json()) as { skill_id: string };
  const skillPath = `${API}/skills/${skillId}`;
  const { evidence, level } = await (await request.get(skillPath)).json();
  const path = `/skills/transfer?skill=${skillId}`;
  await page.goto(path);
  await expect(page.getByRole("heading", { name: "Contrôles de transfert" })).toBeVisible();
  await page.getByLabel("Preuve de compétence").selectOption({
    label: "Idempotence des écritures — Import sans doublons",
  });
  await page.getByLabel("Date d’échéance").fill("2026-11-22");
  await page.getByRole("button", { name: "Programmer un contrôle" }).press("Enter");

  await page.getByRole("button", { name: "Préparer l’exercice" }).press("Enter");
  await expect(page.getByRole("heading", { name: "Une billetterie reçoit deux confirmations" })).toBeVisible();
  await expect(page.getByText("Identifie une clé stable par paiement.")).toHaveCount(0);
  await page.getByRole("textbox", { name: "Ta réponse" }).fill(
    "Je conserve un reçu par identifiant de paiement et le relis lors du rejeu après un arrêt.",
  );
  await page.getByRole("button", { name: "Envoyer pour appréciation" }).press("Enter");
  await expect(page.getByText("Transfert à retravailler", { exact: true })).toBeVisible();
  await expect(page.getByText("Appréciation du", { exact: false })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Journal des contrôles" })).toBeVisible();
  await expect(page.getByText("La clé est stable.", { exact: false })).toBeVisible();
  expect(await (await request.get(skillPath)).json()).toMatchObject({ evidence, level });
});
