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
    // The onboarding gate reads settings before rendering the shell.
    ...settingsApi({ settings: settingsFixture }).handlers,
    http.get(`${apiBaseUrl}/api/v1/health`, () => HttpResponse.json({ status: "ok", checks: {} })),
  );
  render(<App router={createMemoryRouter(buildRoutes(FEATURES), { initialEntries: [path] })} />);
}

describe("App", () => {
  it("shows the home page within the shell", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "Your daily block" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: "Your daily brief" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByText("All services are responding")).toBeInTheDocument();
  });

  it("shows the not-found page for an unknown route", async () => {
    renderAt("/unknown-page");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to home" })).toBeInTheDocument();
  });

  it("sends a new account to the first launch, inside the shell", async () => {
    const api = onboardingApi({ settings: { ...settingsFixture, onboarding_done: false } });
    server.use(...authApi({ me: camille }).handlers, ...api.handlers);
    const router = createMemoryRouter(buildRoutes(FEATURES), {
      initialEntries: ["/learn/council"],
    });
    render(<App router={router} />);
    expect(
      await screen.findByRole("heading", { level: 1, name: "Tremplin's services" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/welcome");
  });
});
