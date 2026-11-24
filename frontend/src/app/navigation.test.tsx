import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, generatePath, matchRoutes, RouterProvider } from "react-router";
import { beforeEach, expect, it } from "vitest";
import { settingsFixture } from "@/features/settings/fixtures";
import { apiBaseUrl } from "@/shared/api/client";
import { authApi, camille } from "@/test/authApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { settingsApi } from "@/test/settingsApi";
import { LEGACY_PATHS } from "./legacyPaths";
import { FEATURES } from "./registry";
import { buildRoutes } from "./router";
import { buildDestinations } from "./navigation";

const overviewUrl = `${apiBaseUrl}/api/v1/lab/overview`;
const preferencesUrl = `${apiBaseUrl}/api/v1/lab/preferences`;

function renderAt(path: string) {
  const router = createMemoryRouter(buildRoutes(FEATURES), { initialEntries: [path] });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return router;
}

beforeEach(() => {
  server.use(
    ...authApi({ me: camille }).handlers,
    ...settingsApi({ settings: settingsFixture }).handlers,
    http.get(`${apiBaseUrl}/api/v1/health`, () => HttpResponse.json({ status: "ok", checks: {} })),
    http.get(overviewUrl, () => HttpResponse.json({ sections: [] })),
    http.get(preferencesUrl, () => HttpResponse.json({ pinned: [], tour: "pending" })),
  );
});

it("ouvre les rubriques et conserve les liens vers les écrans historiques", async () => {
  renderAt("/learn");
  await screen.findByRole("heading", { name: "Étudier" });
  const nav = screen.getByRole("navigation", { name: "Navigation principale" });
  expect(
    within(nav)
      .getAllByRole("link")
      .map((link) => link.textContent),
  ).toEqual(["Accueil", "Étudier", "Coder", "Cerveau", "Carrière", "Labo", "Réglages"]);
  const main = screen.getByRole("main");
  expect(within(main).getByRole("link", { name: /Programmes/ })).toHaveAttribute(
    "href",
    "/learn/programs",
  );
  expect(within(main).getByRole("link", { name: /Leçons/ })).toHaveAttribute(
    "href",
    "/learn/lessons",
  );
});

it("affiche puis épingle une expérience du Labo dans le menu", async () => {
  server.use(
    http.patch(preferencesUrl, async ({ request }) => {
      expect(await request.json()).toEqual({ pinned: ["oncall"] });
      return HttpResponse.json({ pinned: ["oncall"], tour: "pending" });
    }),
  );
  renderAt("/lab");
  await screen.findByRole("heading", { name: "Labo" });
  const main = screen.getByRole("main");
  expect((await within(main).findAllByText("Prête")).length).toBeGreaterThan(1);
  await userEvent.click(within(main).getByRole("button", { name: /Épingler.*Astreinte/i }));
  const nav = screen.getByRole("navigation", { name: "Navigation principale" });
  expect(await within(nav).findByRole("link", { name: /Astreinte/i })).toHaveAttribute(
    "href",
    "/on-call",
  );
});

it("répartit les réglages dans quatre onglets et donne accès aux écrans existants", async () => {
  renderAt("/settings");
  await screen.findByRole("heading", { name: "Réglages" });
  const tabs = screen.getByRole("tablist");
  expect(within(tabs).getAllByRole("tab")).toHaveLength(4);
  const first = within(tabs).getByRole("tab", { name: "Modèles et clés" });
  first.focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(within(tabs).getByRole("tab", { name: "Accès MCP et relais" })).toHaveFocus();
  expect(screen.getByRole("tabpanel")).toHaveTextContent("Accès MCP");
});

it("conserve une destination fonctionnelle pour chaque ancienne entrée", () => {
  const cards = buildDestinations(FEATURES);
  const routes = buildRoutes(FEATURES);
  const paths = new Set(cards.map((card) => card.path));
  for (const entry of FEATURES.flatMap(({ nav }) => nav ?? [])) {
    expect(paths.has(entry.path), entry.path).toBe(true);
    const match = matchRoutes(routes, entry.path)?.at(-1)?.route;
    expect(match && (match.index || match.path !== "*"), entry.path).toBeTruthy();
  }
});

it("keeps every previous page URL and its English destination routable", () => {
  const routes = buildRoutes(FEATURES);
  for (const [before, after] of Object.entries(LEGACY_PATHS)) {
    const params = Object.fromEntries(
      [...before.matchAll(/:(\w+)/g)].map((match) => [match[0].slice(1), "example"]),
    );
    const legacy = matchRoutes(routes, generatePath<string>(before, params))?.at(-1)?.route;
    const current = matchRoutes(routes, generatePath<string>(after, params))?.at(-1)?.route;
    expect(legacy?.path, before).toBe(before);
    expect(current && (current.index || current.path !== "*"), after).toBeTruthy();
  }
});

it("annonce le réglage audio du Podcast à partir des mêmes prérequis que le MCP", async () => {
  server.use(
    http.get(overviewUrl, () =>
      HttpResponse.json({
        sections: [
          { id: "lab", features: [{ id: "podcast", missing_prerequisites: ["openai_audio"] }] },
        ],
      }),
    ),
  );
  renderAt("/lab");
  const message = await screen.findByText("Pour écouter le podcast, ajoute une clé OpenAI.");
  const card = message.closest("li");
  expect(card).not.toBeNull();
  expect(
    within(card!).getByRole("link", { name: "Vérifier les modèles et les clés" }),
  ).toHaveAttribute("href", "/settings/models");
  expect(within(card!).queryByText("Prête")).toBeNull();
});
