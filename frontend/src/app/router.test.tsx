import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import type { FeatureManifest } from "@/shared/lib/feature";
import { authApi, camille } from "@/test/authApi";
import { settingsFixture } from "@/features/settings/fixtures";
import { settingsApi } from "@/test/settingsApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { buildRoutes } from "./router";

const features: FeatureManifest[] = [
  { id: "demo", routes: [{ path: "/demo", element: <h1>Démo</h1> }] },
  {
    id: "public",
    routes: [],
    publicRoutes: [{ path: "/ouverte", element: <h1>Page ouverte</h1> }],
    legacyPublicRoutes: { "/ancienne": "/ouverte" },
  },
];

function renderAt(path: string, me: typeof camille | null = camille) {
  const auth = authApi({ me });
  server.use(
    ...auth.handlers,
    // La porte du premier lancement lit les réglages avant la mise en page.
    ...settingsApi({ settings: settingsFixture }).handlers,
    http.get(`${apiBaseUrl}/api/v1/health`, () => HttpResponse.json({ status: "ok", checks: {} })),
  );
  const router = createMemoryRouter(buildRoutes(features), { initialEntries: [path] });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { auth, router };
}

describe("buildRoutes", () => {
  it("mounts manifest routes in AppLayout", async () => {
    renderAt("/demo");
    expect(await screen.findByRole("heading", { name: "Démo" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
  });

  it("ends with the not-found page", async () => {
    renderAt("/nimporte-quoi");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("public routes render without layout or gates", async () => {
    // Sans session : la porte renverrait vers `/login`, mais une route publique ne la traverse
    // pas.
    const { auth } = renderAt("/ouverte", null);
    expect(await screen.findByRole("heading", { name: "Page ouverte" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.queryByRole("banner")).toBeNull();
    expect(auth.meCalls).toBe(0);
  });

  it("redirects previous public routes and preserves the query and fragment", async () => {
    const { auth, router } = renderAt("/ancienne?error=expired#continue", null);
    expect(await screen.findByRole("heading", { name: "Page ouverte" })).toBeInTheDocument();
    expect(router.state.location).toMatchObject({
      pathname: "/ouverte",
      search: "?error=expired",
      hash: "#continue",
    });
    expect(auth.meCalls).toBe(0);
  });
});
