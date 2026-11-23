import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { settingsFixture } from "@/features/settings/fixtures";
import { authApi, camille } from "@/test/authApi";
import { settingsApi } from "@/test/settingsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { AppLayout } from "./AppLayout";

// Une feature de plus, qui déclare les deux emplacements de la coquille.
vi.mock("../../registry", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../registry")>();
  return {
    FEATURES: [
      ...original.FEATURES,
      {
        id: "slots",
        routes: [],
        shell: {
          topbar: () => <span>Emplacement du haut</span>,
          overlay: () => <div role="dialog" aria-label="Surcouche" />,
        },
      },
    ],
  };
});

describe("AppLayout", () => {
  // Les portes lisent `me` (connexion), puis les réglages (premier lancement), avant la page.
  beforeEach(() =>
    server.use(
      ...authApi({ me: camille }).handlers,
      ...settingsApi({ settings: settingsFixture }).handlers,
    ),
  );

  it("rend le lien d'évitement, la navigation, le voyant et le contenu", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    );
    const router = createMemoryRouter([
      { path: "/", Component: AppLayout, children: [{ index: true, element: <p>Contenu</p> }] },
    ]);
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });

    expect(await screen.findByRole("link", { name: "Aller au contenu" })).toHaveAttribute(
      "href",
      "#contenu",
    );
    const banner = screen.getByRole("banner");
    const panel = screen.getByRole("complementary", { name: "Repères et informations" });
    expect(within(panel).getByRole("link", { name: "Tremplin" })).toHaveAttribute("href", "/");
    const nav = within(banner).getByRole("navigation", { name: "Navigation principale" });
    expect(within(nav).getByRole("link", { name: "Étudier" })).toHaveAttribute(
      "href",
      "/etudier",
    );
    expect(within(nav).getByRole("link", { name: "Accueil" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "contenu");
    expect(main).toHaveAttribute("tabindex", "-1");
    expect(main).toHaveTextContent("Contenu");
    expect(
      await within(panel).findByText("Tous les services répondent"),
    ).toBeInTheDocument();
  });

  it("donne plus de largeur à une page qui le demande (handle wide), pas aux autres", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    );
    const router = createMemoryRouter(
      [
        {
          path: "/",
          Component: AppLayout,
          children: [
            { index: true, element: <p>Étroite</p> },
            { path: "large", handle: { wide: true }, element: <p>Large</p> },
          ],
        },
      ],
      { initialEntries: ["/large"] },
    );
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    await screen.findByText("Large");
    expect(screen.getByRole("main").className).toContain("max-w-7xl");
    expect(screen.getByRole("main").className).not.toContain("max-w-4xl");
  });

  it("garde la colonne étroite par défaut", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    );
    const router = createMemoryRouter([
      { path: "/", Component: AppLayout, children: [{ index: true, element: <p>Étroite</p> }] },
    ]);
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    await screen.findByText("Étroite");
    expect(screen.getByRole("main").className).toContain("max-w-4xl");
  });

  it("hides the menus, the panel and the health light on a bare page (handle bare)", async () => {
    let healthReads = 0;
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () => {
        healthReads += 1;
        return HttpResponse.json({ status: "ok", checks: {} });
      }),
    );
    const router = createMemoryRouter(
      [
        {
          path: "/",
          Component: AppLayout,
          children: [{ path: "nue", handle: { bare: true }, element: <p>Nue</p> }],
        },
      ],
      { initialEntries: ["/nue"] },
    );
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    await screen.findByText("Nue");
    expect(screen.queryByRole("navigation", { name: "Navigation principale" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Tremplin" })).toBeNull();
    expect(screen.queryByRole("complementary")).toBeNull();
    expect(screen.queryByText("Tous les services répondent")).toBeNull();
    // La barre du haut reste (compte, déconnexion) ; seul le voyant, qui lit `/health`, s'en va.
    expect(within(screen.getByRole("banner")).getByText("Emplacement du haut")).toBeInTheDocument();
    expect(healthReads).toBe(0);
  });

  it("renders the topbar slots of features in the left panel, not in the top bar", async () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    );
    const router = createMemoryRouter([
      { path: "/", Component: AppLayout, children: [{ index: true, element: <p>Contenu</p> }] },
    ]);
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    const panel = await screen.findByRole("complementary", { name: "Repères et informations" });
    expect(within(panel).getByText("Emplacement du haut")).toBeInTheDocument();
    expect(within(screen.getByRole("banner")).queryByText("Emplacement du haut")).toBeNull();
    expect(screen.getByRole("dialog", { name: "Surcouche" })).toBeInTheDocument();
    expect(within(screen.getByRole("banner")).queryByRole("dialog")).toBeNull();
  });
});
