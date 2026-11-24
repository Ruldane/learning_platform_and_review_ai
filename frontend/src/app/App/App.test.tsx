import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { createMemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { authApi, camille } from "@/test/authApi";
import { homeApi } from "@/test/homeApi";
import { onboardingApi } from "@/test/onboardingApi";
import { settingsApi } from "@/test/settingsApi";
import { server } from "@/test/server";
import { settingsFixture } from "@/features/settings/fixtures";
import { FEATURES } from "../registry";
import { buildRoutes } from "../router";
import { App } from "./App";

function renderAt(path: string) {
  server.use(
    ...authApi({ me: camille }).handlers,
    ...homeApi().handlers,
    // La porte du premier lancement lit les réglages avant la mise en page.
    ...settingsApi({ settings: settingsFixture }).handlers,
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

  it("sends a new account to the first launch, inside the shell", async () => {
    const api = onboardingApi({ settings: { ...settingsFixture, onboarding_done: false } });
    server.use(...authApi({ me: camille }).handlers, ...api.handlers);
    const router = createMemoryRouter(buildRoutes(FEATURES), {
      initialEntries: ["/learn/council"],
    });
    render(<App router={router} />);
    expect(
      await screen.findByRole("heading", { level: 1, name: "Les services de Tremplin" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/welcome");
  });
});
