import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

async function capture(page: Page, name: string) {
  const destination = process.env.E2E_REORGANISATION_CAPTURES;
  if (!destination) return;
  await mkdir(destination, { recursive: true });
  await page.screenshot({ path: join(destination, `${name}.png`), animations: "disabled" });
}

test("les rubriques, les anciennes adresses et les raccourcis du Labo", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Navigation principale" });
  const main = page.getByRole("main");
  await expect(main.getByRole("heading", { name: "Ton brief du jour" })).toBeVisible();
  await expect(main.getByRole("heading", { name: "Révisions" })).toBeVisible();
  await expect(main.getByRole("link", { name: /Voir la pile de lecture/ })).toBeVisible();
  await expect(nav.getByRole("link")).toHaveCount(7);
  await capture(page, "accueil");

  await page.setViewportSize({ width: 768, height: 900 });
  await nav.getByRole("button", { name: /^Menu/ }).click();
  await expect(nav.getByRole("link")).toHaveCount(7);
  await capture(page, "menu");
  await nav.getByRole("link", { name: /^Étudier/ }).click();
  await expect(main).toBeFocused();
  await page.setViewportSize({ width: 1280, height: 900 });
  await expect(main.getByRole("heading", { name: "Étudier" })).toBeVisible();
  await expect(main.getByRole("link", { name: "Ouvrir Programmes" })).toHaveAttribute(
    "href",
    "/apprendre/programme",
  );
  await capture(page, "etudier");

  await nav.getByRole("link", { name: "Labo" }).click();
  await expect(main.getByRole("heading", { name: "Labo", exact: true })).toBeVisible();
  const podcast = main.locator('li[data-feature="podcast"]');
  await expect(podcast.getByText("Pour écouter le podcast, ajoute une clé OpenAI.")).toBeVisible();
  await expect(
    podcast.getByRole("link", { name: "Vérifier les modèles et les clés" }),
  ).toHaveAttribute("href", "/reglages/modeles");
  const pin = main.getByRole("button", { name: "Épingler Astreinte" });
  await expect(pin).toBeEnabled();
  await capture(page, "labo");
  await pin.click();
  await expect(nav.getByRole("link", { name: "Astreinte" })).toBeVisible();
  await page.reload();
  await expect(nav.getByRole("link", { name: "Astreinte" })).toBeVisible();
  await main.getByRole("button", { name: "Désépingler Astreinte" }).click();
  await expect(nav.getByRole("link", { name: "Astreinte" })).toHaveCount(0);

  await page.goto("/memoire/cerveau");
  await expect(main.getByRole("heading", { name: "Cerveau", exact: true })).toBeVisible();
  const connection = main.getByRole("complementary", { name: "État du relais" });
  await expect(connection.getByRole("status")).not.toHaveText("Vérification du relais…");
  if (process.env.E2E_REORGANISATION_CAPTURES) {
    await expect(connection.getByRole("status")).toHaveText(
      "Relais de synchronisation à configurer",
    );
    await expect(connection.getByText(/TREMPLIN_BRAIN_SYNC_TOKEN/)).toBeVisible();
  }
  await capture(page, "cerveau-sans-relais");
});

test("la carte MCP et les épingles du Labo correspondent aux destinations de l’interface", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const overview = await request.get(`${API}/lab/overview`);
  expect(overview.ok()).toBe(true);
  const { sections } = (await overview.json()) as {
    sections: { id: string; local_url: string; features: { id: string }[] }[];
  };
  const preferences = `${API}/lab/preferences`;
  const before = (await (await request.get(preferences)).json()) as { pinned: string[] };
  for (const section of sections.filter(({ id }) => id !== "home")) {
    await page.goto(section.local_url);
    const cards = page.getByRole("main").locator("li[data-feature]");
    await expect(cards.first()).toBeVisible();
    const visibleIds = await cards.evaluateAll((nodes) =>
      [...new Set(nodes.flatMap((node) => node.getAttribute("data-feature") ?? []))].sort(),
    );
    const overviewIds = section.features.map(({ id }) => id).sort();
    expect(overviewIds).toEqual(expect.arrayContaining(visibleIds));
    if (section.id !== "lab") continue;
    expect(visibleIds).toEqual(overviewIds);
    try {
      const accepted = await request.patch(preferences, { data: { pinned: visibleIds } });
      expect(accepted.ok()).toBe(true);
      expect(await accepted.json()).toMatchObject({ pinned: visibleIds });
    } finally {
      await request.patch(preferences, { data: { pinned: before.pinned } });
    }
  }
});
