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

const PANEL = { name: "Repères et informations" };

describe("AppLayout, panneau de gauche", () => {
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

  it("met le nom, la santé et le contenu des emplacements dans le panneau, à côté du contenu", async () => {
    renderAt("/");
    const panel = await screen.findByRole("complementary", PANEL);
    expect(within(panel).getByRole("link", { name: "Tremplin" })).toHaveAttribute("href", "/");
    expect(await within(panel).findByText("Tous les services répondent")).toBeInTheDocument();
    expect(within(panel).getByText("Info de feature")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: /Capture rapide/ })).toBeInTheDocument();
    // Étroit, fixe, et le contenu reste centré à sa droite.
    expect(panel.className).toContain("w-60");
    expect(panel.firstElementChild?.className).toContain("sticky");
    expect(screen.getByRole("main").className).toContain("mx-auto");
    expect(panel.parentElement).toBe(screen.getByRole("main").parentElement);
    // Dans la barre du haut : seulement les menus.
    const banner = screen.getByRole("banner");
    expect(within(banner).queryByText("Tous les services répondent")).toBeNull();
    expect(within(banner).queryByRole("button", { name: /Capture rapide/ })).toBeNull();
    expect(within(banner).getByRole("navigation", { name: "Navigation principale" })).toBeVisible();
  });

  it("affiche « Tu es ici » avec la section et la page", async () => {
    renderAt("/reglages/couts");
    const here = within(await screen.findByRole("complementary", PANEL)).getByRole("group", {
      name: "Tu es ici",
    });
    expect(here).toHaveTextContent("Réglages › Coûts");
    expect(here).toHaveAttribute("data-section", "settings");
    expect(within(here).getByTestId("section-dot").style.backgroundColor).toBe(
      "var(--section-settings)",
    );
  });

  it("n'écrit que le nom d'une section d'une seule page", async () => {
    renderAt("/");
    const here = within(await screen.findByRole("complementary", PANEL)).getByRole("group", {
      name: "Tu es ici",
    });
    expect(here).toHaveTextContent(/^Tu es ici\s*Accueil$/);
  });

  it("colore la section active du menu et marque la page courante", async () => {
    renderAt("/reglages/couts");
    await screen.findByRole("complementary", PANEL);
    const nav = screen.getByRole("navigation", { name: "Navigation principale" });
    const settings = within(nav).getByRole("button", { name: "Réglages" });
    expect(settings).toHaveAttribute("data-active", "true");
    expect(settings.style.getPropertyValue("--section-color")).toBe("var(--section-settings)");
    expect(settings.className).toContain("border-[var(--section-color)]");
  });

  it("ne montre pas « Tu es ici » hors de la navigation", async () => {
    renderAt("/introuvable");
    const panel = await screen.findByRole("complementary", PANEL);
    expect(within(panel).queryByRole("group", { name: "Tu es ici" })).toBeNull();
  });

  describe("écran étroit", () => {
    beforeEach(() =>
      vi.stubGlobal("matchMedia", () => ({
        matches: true,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      })),
    );

    it("replie le panneau en une ligne sous la barre, les menus dans le bouton Menu", async () => {
      renderAt("/reglages/couts");
      const line = await screen.findByRole("complementary", PANEL);
      const banner = screen.getByRole("banner");
      expect(line.className).not.toContain("w-60");
      expect(line.previousElementSibling).toBe(banner);
      expect(within(line).getByRole("group", { name: "Tu es ici" })).toHaveTextContent(
        "Réglages › Coûts",
      );
      expect(await within(line).findByText("Tous les services répondent")).toBeInTheDocument();
      expect(within(line).getByText("Info de feature")).toBeInTheDocument();
      expect(within(banner).getByRole("button", { name: "Menu" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Réglages" })).toBeNull();
      // Un seul panneau, jamais deux exemplaires des emplacements.
      expect(screen.getAllByText("Info de feature")).toHaveLength(1);
    });
  });
});
