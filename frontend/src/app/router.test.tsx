import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import type { FeatureManifest } from "@/shared/lib/feature";
import { authApi, camille } from "@/test/authApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { buildRoutes } from "./router";

const features: FeatureManifest[] = [
  { id: "demo", routes: [{ path: "/demo", element: <h1>Démo</h1> }] },
  {
    id: "public",
    routes: [],
    publicRoutes: [{ path: "/ouverte", element: <h1>Page ouverte</h1> }],
  },
];

function renderAt(path: string, me: typeof camille | null = camille) {
  const auth = authApi({ me });
  server.use(
    ...auth.handlers,
    http.get(`${apiBaseUrl}/api/v1/health`, () => HttpResponse.json({ status: "ok", checks: {} })),
  );
  const router = createMemoryRouter(buildRoutes(features), { initialEntries: [path] });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { auth };
}

describe("buildRoutes", () => {
  it("monte les routes des manifestes dans AppLayout", async () => {
    renderAt("/demo");
    expect(await screen.findByRole("heading", { name: "Démo" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Navigation principale" })).toBeInTheDocument();
  });

  it("termine par la page introuvable", async () => {
    renderAt("/nimporte-quoi");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
  });

  it("public routes render without layout or gates", async () => {
    // Sans session : la porte renverrait vers `/connexion`, mais une route publique ne la traverse pas.
    const { auth } = renderAt("/ouverte", null);
    expect(await screen.findByRole("heading", { name: "Page ouverte" })).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.queryByRole("banner")).toBeNull();
    expect(auth.meCalls).toBe(0);
  });
});
