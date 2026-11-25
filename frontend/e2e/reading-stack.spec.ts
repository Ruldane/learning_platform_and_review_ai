import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test("ouvre une lecture au clavier sur mobile et enregistre son état", async ({ page, request }) => {
  await finishFirstLaunch(request);
  const entry = {
    id: "lecture-e2e",
    kind: "article",
    title: "Comprendre un flux RSS",
    summary: "Une lecture synthétique sur les flux.",
    text: "Voici le texte lisible de la publication.",
    reason: "Flux suivi",
    url: "https://example.org/reading",
    company: null,
    created_at: "2026-11-22T08:00:00Z",
    read_at: null as string | null,
  };
  await page.setViewportSize({ width: 375, height: 800 });
  await page.route(/\/api\/v1\/reading-stack(?:\?|$)/, (route) =>
    route.fulfill({
      json: {
        items: entry.read_at ? [] : [entry],
        unread_count: Number(!entry.read_at),
        next_offset: null,
      },
    }),
  );
  await page.route("**/api/v1/reading-stack/lecture-e2e", (route) => {
    if (route.request().method() === "PATCH") {
      expect(route.request().postDataJSON()).toEqual({ read: true });
      entry.read_at = entry.created_at;
    }
    return route.fulfill({ json: entry });
  });
  await page.goto("/memory/reading");
  const link = page.getByRole("link", { name: entry.title });
  await link.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: entry.title })).toBeFocused();
  await expect(page.getByText(entry.text)).toBeVisible();
  await page.getByRole("button", { name: "Marquer comme lu" }).click();
  await expect(page.getByRole("button", { name: "Marquer comme non lu" })).toBeEnabled();
  await expect(page.getByText("0 éléments non lus")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(375);
});
