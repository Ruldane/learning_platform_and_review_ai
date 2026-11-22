import { expect, test } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test("appaire, renouvelle et révoque le relais depuis Accès MCP", async ({ page, request }) => {
  await finishFirstLaunch(request);
  expect((await request.put(`${API}/mcp/settings`, { data: { enabled: true } })).ok()).toBe(true);
  let exchanges = 0;
  await page.route("http://127.0.0.1:8770/pair", async (route) => {
    const origin = new URL(page.url()).origin;
    const headers = {
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": "POST",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Allow-Private-Network": "true",
    };
    if (route.request().method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers });
      return;
    }
    const data: unknown = route.request().postDataJSON();
    const exchanged = await request.post(`${API}/mcp/relay/exchange`, { data });
    expect(exchanged.status()).toBe(201);
    exchanges += 1;
    await route.fulfill({ status: 204, headers });
  });

  await page.goto("/reglages/mcp");
  const relay = page.getByRole("heading", { name: "Relais local" }).locator("../..");
  await relay.getByRole("button", { name: "Connecter le relais" }).click();
  await expect(relay.getByText("Relais connecté")).toBeVisible();
  await relay.getByRole("button", { name: "Renouveler l’appairage" }).click();
  await expect.poll(() => exchanges).toBe(2);
  await expect(relay.getByText("Relais connecté")).toBeVisible();
  await relay.getByRole("button", { name: "Révoquer l’appairage" }).click();
  await expect(relay.getByText("Appairage révoqué")).toBeVisible();
});
