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

it("opens sections and links to their pages", async () => {
  renderAt("/learn");
  await screen.findByRole("heading", { name: "Learn" });
  const nav = screen.getByRole("navigation", { name: "Main navigation" });
  expect(
    within(nav)
      .getAllByRole("link")
      .map((link) => link.textContent),
  ).toEqual(["Home", "Learn", "Code", "Brain", "Career", "Lab", "Settings"]);
  const main = screen.getByRole("main");
  expect(within(main).getByRole("link", { name: /Programs/ })).toHaveAttribute(
    "href",
    "/learn/programs",
  );
  expect(within(main).getByRole("link", { name: /Lessons/ })).toHaveAttribute(
    "href",
    "/learn/lessons",
  );
});

it("shows a Lab activity and pins it to the menu", async () => {
  server.use(
    http.patch(preferencesUrl, async ({ request }) => {
      expect(await request.json()).toEqual({ pinned: ["oncall"] });
      return HttpResponse.json({ pinned: ["oncall"], tour: "pending" });
    }),
  );
  renderAt("/lab");
  await screen.findByRole("heading", { name: "Lab" });
  const main = screen.getByRole("main");
  expect((await within(main).findAllByText("Ready")).length).toBeGreaterThan(1);
  await userEvent.click(within(main).getByRole("button", { name: /^Pin.*On-call/i }));
  const nav = screen.getByRole("navigation", { name: "Main navigation" });
  expect(await within(nav).findByRole("link", { name: /On-call/i })).toHaveAttribute(
    "href",
    "/on-call",
  );
});

it("uses four settings tabs with keyboard navigation", async () => {
  renderAt("/settings");
  await screen.findByRole("heading", { name: "Settings" });
  const tabs = screen.getByRole("tablist");
  expect(within(tabs).getAllByRole("tab")).toHaveLength(4);
  const first = within(tabs).getByRole("tab", { name: "Models and keys" });
  first.focus();
  await userEvent.keyboard("{ArrowRight}");
  expect(within(tabs).getByRole("tab", { name: "MCP access and relay" })).toHaveFocus();
  expect(screen.getByRole("tabpanel")).toHaveTextContent("MCP access");
});

it("assigns a working destination to each navigation entry", () => {
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

it("shows the shared MCP prerequisite for podcast audio", async () => {
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
  const message = await screen.findByText("To listen to the podcast, add an OpenAI key.");
  const card = message.closest("li");
  expect(card).not.toBeNull();
  expect(
    within(card!).getByRole("link", { name: "Check models and keys" }),
  ).toHaveAttribute("href", "/settings/models");
  expect(within(card!).queryByText("Ready")).toBeNull();
});
