import { expect, test } from "@playwright/test";
import type { components } from "../src/shared/api/schema.d.ts";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(process.env.E2E_CALENDAR !== "1", "Requiert l’Agenda synthétique tests.e2e.calendar.");

test("autorise Agenda, décale un bloc occupé et confirme son créneau", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const pageOfPrograms = await request.get(API + "/programs");
  expect(pageOfPrograms.ok()).toBe(true);
  const [program] = (await pageOfPrograms.json()) as components["schemas"]["ProgramSummaryOut"][];
  expect(program?.status).toBe("validated");
  await page.goto("/settings/calendar", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Connecter Google Agenda" }).click();
  await expect(page).toHaveURL(/\/settings\/calendar\?calendar=connected$/, { timeout: 20_000 });
  await expect(page.getByText("Google Agenda est connecté.")).toBeVisible({ timeout: 25_000 });

  await page.goto("/learn/programs/" + program!.id + "/replan", {
    waitUntil: "domcontentloaded",
  });
  await page.getByRole("button", { name: "Replanifier", exact: true }).click();
  const accept = page.getByRole("button", { name: "Accepter le nouveau plan" });
  await expect(accept).toBeVisible({ timeout: 20000 });
  await accept.click();
  await expect(page.getByText("Nouveau plan accepté : ton programme est à jour.")).toBeVisible();

  const latest = await request.get(API + "/programs/" + program!.id);
  expect(latest.ok()).toBe(true);
  const plan = (await latest.json()) as components["schemas"]["ProgramOut"];
  expect(
    plan.diff?.moved.some((move) => move.before === "2026-11-16" && move.after > move.before),
  ).toBe(true);
  await page.getByRole("link", { name: "Synchroniser dans Google Agenda" }).click();
  const task = plan.weeks
    .flatMap((week) => week.modules.flatMap((module) => module.tasks))
    .find((item) => item.status === "todo" && item.planned_date > "2026-11-16");
  expect(task).toBeDefined();
  await page.getByRole("combobox", { name: "Bloc d’étude" }).selectOption(task!.id);
  await page.getByRole("button", { name: "Préparer un aperçu" }).click();
  const heading = page.getByRole("heading", { name: "Ajouter à Google Agenda" });
  await expect(heading).toBeFocused();
  expect(await (await request.get(API + "/calendar/upcoming")).json()).toBeNull();
  await page.keyboard.press("Tab");
  const confirm = page.getByRole("button", { name: "Confirmer la synchronisation" });
  await expect(confirm).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Événement synchronisé.")).toBeVisible();
  const next = (await (
    await request.get(API + "/calendar/upcoming")
  ).json()) as components["schemas"]["UpcomingEvent"];
  expect(next.kind).toBe("study");
  expect(next.start.startsWith(task!.planned_date)).toBe(true);
});
