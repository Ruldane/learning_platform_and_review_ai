import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { settingsFixture } from "@/features/settings/fixtures";
import { authApi, camille } from "@/test/authApi";
import { settingsApi } from "@/test/settingsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { AppLayout } from "./AppLayout";

// Une feature de plus, qui déclare un emplacement `topbar` : il doit finir dans le panneau.
vi.mock("../../registry", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../registry")>();
  return {
    FEATURES: [
      ...original.FEATURES,
      { id: "slots", routes: [], shell: { topbar: () => <span>Info de feature</span> } },
    ],
  };
});

function renderAt(path: string) {
  const router = createMemoryRouter(
    [{ path: "*", Component: AppLayout, children: [{ path: "*", element: <p>Contenu</p> }] }],
    { initialEntries: [path] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
}

const PANEL = { name: "Landmarks and information" };

describe("AppLayout side panel", () => {
  beforeEach(() =>
    server.use(
      ...authApi({ me: camille }).handlers,
      ...settingsApi({ settings: settingsFixture }).handlers,
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    ),
  );
  afterEach(() => vi.unstubAllGlobals());

  it("puts the app name, service status and slots in the side panel", async () => {
    renderAt("/");
    const panel = await screen.findByRole("complementary", PANEL);
    expect(within(panel).getByRole("link", { name: "Tremplin" })).toHaveAttribute("href", "/");
    expect(await within(panel).findByText("All services are responding")).toBeInTheDocument();
    expect(within(panel).getByText("Info de feature")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: /Quick capture/ })).toBeInTheDocument();
    // Étroit, fixe, et le contenu reste centré à sa droite.
    expect(panel.className).toContain("w-60");
    expect(panel.firstElementChild?.className).toContain("sticky");
    expect(screen.getByRole("main").className).toContain("mx-auto");
    expect(panel.parentElement).toBe(screen.getByRole("main").parentElement);
    // Dans la barre du haut : seulement les menus.
    const banner = screen.getByRole("banner");
    expect(within(banner).queryByText("All services are responding")).toBeNull();
    expect(within(banner).queryByRole("button", { name: /Quick capture/ })).toBeNull();
    expect(within(banner).getByRole("navigation", { name: "Main navigation" })).toBeVisible();
  });

  it("shows the current section and page", async () => {
    renderAt("/settings/costs");
    const here = within(await screen.findByRole("complementary", PANEL)).getByRole("group", {
      name: "You are here",
    });
    expect(here).toHaveTextContent("Settings › Costs");
    expect(here).toHaveAttribute("data-section", "settings");
    expect(within(here).getByTestId("section-dot").style.backgroundColor).toBe(
      "var(--section-settings)",
    );
  });

  it("shows a single name for a one-page section", async () => {
    renderAt("/");
    const here = within(await screen.findByRole("complementary", PANEL)).getByRole("group", {
      name: "You are here",
    });
    expect(here).toHaveTextContent(/^You are here\s*Home$/);
  });

  it("colours the active menu section and marks the current location", async () => {
    renderAt("/settings/costs");
    await screen.findByRole("complementary", PANEL);
    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    const settings = within(nav).getByRole("link", { name: "Settings" });
    expect(settings).toHaveAttribute("data-active", "true");
    expect(settings).toHaveAttribute("aria-current", "location");
    expect(settings.style.getPropertyValue("--section-color")).toBe("var(--section-settings)");
    expect(settings.className).toContain("border-[var(--section-color)]");
  });

  it("hides the location indicator outside the navigation", async () => {
    renderAt("/introuvable");
    const panel = await screen.findByRole("complementary", PANEL);
    expect(within(panel).queryByRole("group", { name: "You are here" })).toBeNull();
  });

  describe("narrow screen", () => {
    beforeEach(() =>
      vi.stubGlobal("matchMedia", () => ({
        matches: true,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      })),
    );

    it("shows the panel below the top bar and puts navigation in the Menu button", async () => {
      renderAt("/settings/costs");
      const line = await screen.findByRole("complementary", PANEL);
      const banner = screen.getByRole("banner");
      expect(line.className).not.toContain("w-60");
      expect(line.previousElementSibling).toBe(banner);
      expect(within(line).getByRole("group", { name: "You are here" })).toHaveTextContent(
        "Settings › Costs",
      );
      expect(await within(line).findByText("All services are responding")).toBeInTheDocument();
      expect(within(line).getByText("Info de feature")).toBeInTheDocument();
      expect(within(banner).getByRole("button", { name: "Menu" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Settings" })).toBeNull();
      // Un seul panneau, jamais deux exemplaires des emplacements.
      expect(screen.getAllByText("Info de feature")).toHaveLength(1);
    });
  });
});
