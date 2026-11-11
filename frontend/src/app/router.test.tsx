import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import type { FeatureManifest } from "@/shared/lib/feature";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { buildRoutes } from "./router";

const features: FeatureManifest[] = [
  { id: "demo", routes: [{ path: "/demo", element: <h1>Démo</h1> }] },
];

function renderAt(path: string) {
  server.use(
    http.get(`${apiBaseUrl}/api/v1/health`, () => HttpResponse.json({ status: "ok", checks: {} })),
  );
  const router = createMemoryRouter(buildRoutes(features), { initialEntries: [path] });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
}

describe("buildRoutes", () => {
  it("monte les routes des manifestes dans AppLayout", () => {
    renderAt("/demo");
    expect(screen.getByRole("heading", { name: "Démo" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Navigation principale" })).toBeInTheDocument();
  });

  it("termine par la page introuvable", () => {
    renderAt("/nimporte-quoi");
    expect(screen.getByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
  });
});
