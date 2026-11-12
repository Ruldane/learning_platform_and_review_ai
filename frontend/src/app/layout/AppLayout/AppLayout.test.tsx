import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
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

    expect(screen.getByRole("link", { name: "Aller au contenu" })).toHaveAttribute(
      "href",
      "#contenu",
    );
    expect(screen.getByRole("navigation", { name: "Navigation principale" })).toBeInTheDocument();
    const main = screen.getByRole("main");
    expect(main).toHaveAttribute("id", "contenu");
    expect(main).toHaveAttribute("tabindex", "-1");
    expect(main).toHaveTextContent("Contenu");
    expect(await screen.findByText("Tous les services répondent")).toBeInTheDocument();
  });

  it("donne plus de largeur à une page qui le demande (handle wide), pas aux autres", () => {
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
    expect(screen.getByRole("main").className).toContain("max-w-7xl");
    expect(screen.getByRole("main").className).not.toContain("max-w-4xl");
  });

  it("garde la colonne étroite par défaut", () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    );
    const router = createMemoryRouter([
      { path: "/", Component: AppLayout, children: [{ index: true, element: <p>Étroite</p> }] },
    ]);
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    expect(screen.getByRole("main").className).toContain("max-w-4xl");
  });

  it("renders shell slots of features", () => {
    server.use(
      http.get(`${apiBaseUrl}/api/v1/health`, () =>
        HttpResponse.json({ status: "ok", checks: {} }),
      ),
    );
    const router = createMemoryRouter([
      { path: "/", Component: AppLayout, children: [{ index: true, element: <p>Contenu</p> }] },
    ]);
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    expect(within(screen.getByRole("banner")).getByText("Emplacement du haut")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Surcouche" })).toBeInTheDocument();
    expect(within(screen.getByRole("banner")).queryByRole("dialog")).toBeNull();
  });
});
