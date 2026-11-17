import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { authApi, camille } from "@/test/authApi";
import { homeApi } from "@/test/homeApi";
import { server } from "@/test/server";
import { FEATURES } from "../registry";
import { buildRoutes } from "../router";
import { App } from "./App";

function renderAt(path: string) {
  server.use(
    ...authApi({ me: camille }).handlers,
    ...homeApi().handlers,
    http.get(`${apiBaseUrl}/api/v1/health`, () => HttpResponse.json({ status: "ok", checks: {} })),
  );
  render(<App router={createMemoryRouter(buildRoutes(FEATURES), { initialEntries: [path] })} />);
}

describe("App", () => {
  it("affiche l'accueil dans la coquille", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "Ton bloc du jour" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Ton brief du jour" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Accueil" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByText("Tous les services répondent")).toBeInTheDocument();
  });

  it("affiche la page introuvable pour une route inconnue", async () => {
    renderAt("/nimporte-quoi");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retour à l'accueil" })).toBeInTheDocument();
  });
});
