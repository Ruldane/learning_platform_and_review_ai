import { QueryClient } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { onboardingApi } from "@/test/onboardingApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { settingsFixture } from "./fixtures";
import { OnboardingGate } from "./OnboardingGate";
import { WelcomePage } from "./pages/WelcomePage";

const fresh = { ...settingsFixture, onboarding_done: false };

function setup(over: Parameters<typeof onboardingApi>[0], at = "/") {
  const api = onboardingApi(over);
  server.use(...api.handlers);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <OnboardingGate>
            <Outlet />
          </OnboardingGate>
        ),
        children: [
          {
            index: true,
            element: (
              <main id="contenu" tabIndex={-1}>
                Accueil de Tremplin
              </main>
            ),
          },
          { path: "learn", element: <p>Learn</p> },
          { path: "welcome", element: <WelcomePage /> },
        ],
      },
    ],
    { initialEntries: [at] },
  );
  const Wrapper = createQueryWrapper(client);
  render(
    <Wrapper>
      <RouterProvider router={router} />
    </Wrapper>,
  );
  const view = { client, router, user: userEvent.setup() };
  // Une entrée par changement de chemin : « une seule redirection » se compte ici.
  const visited = [router.state.location.pathname];
  router.subscribe((state) => {
    if (visited[visited.length - 1] !== state.location.pathname) {
      visited.push(state.location.pathname);
    }
  });
  return { ...api, ...view, visited };
}

describe("OnboardingGate", () => {
  it("gate sends a new account to /welcome", async () => {
    const { router, visited } = setup({ settings: fresh }, "/learn");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Tremplin's services" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Learn")).toBeNull();
    expect(router.state.location.pathname).toBe("/welcome");
    // Un remplacement : « précédent » ne ramène pas à une porte qui renverrait aussitôt.
    expect(router.state.historyAction).toBe("REPLACE");
    expect(visited).toEqual(["/learn", "/welcome"]);
  });

  it("gate lets an onboarded account through", async () => {
    const { router, visited } = setup({ settings: settingsFixture }, "/learn");
    expect(await screen.findByText("Learn")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/learn");
    expect(visited).toEqual(["/learn"]);
  });

  it("does not send a new account away from /welcome, nor loop", async () => {
    const { visited } = setup({ settings: fresh }, "/welcome");
    await screen.findByRole("heading", { level: 1, name: "Tremplin's services" });
    expect(visited).toEqual(["/welcome"]);
  });

  it("keeps the layout away while the settings are read", async () => {
    const { reads } = setup({ settings: settingsFixture });
    expect(screen.getByRole("status")).toHaveTextContent("Preparing your space");
    expect(screen.queryByText("Accueil de Tremplin")).toBeNull();
    await screen.findByText("Accueil de Tremplin");
    expect(reads.settings).toBe(1);
  });

  it("shows the failure, and a retry that hands the focus to the page content", async () => {
    const { user, reads } = setup({ settings: settingsFixture, settingsFailures: 1 });
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur a échoué.");
    expect(screen.queryByText("Accueil de Tremplin")).toBeNull();
    const retry = screen.getByRole("button", { name: "Retry" });
    retry.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("Accueil de Tremplin")).toHaveFocus();
    expect(reads.settings).toBe(2);
  });

  it("after a retry that leads to /welcome, the focus is the title of the step", async () => {
    const { user, router } = setup({ settings: fresh, settingsFailures: 1 });
    await user.click(await screen.findByRole("button", { name: "Retry" }));
    const title = await screen.findByRole("heading", {
      level: 1,
      name: "Tremplin's services",
    });
    await waitFor(() => expect(title).toHaveFocus());
    expect(router.state.location.pathname).toBe("/welcome");
  });

  it("a failed re-read, with the settings already there, never closes the app", async () => {
    const { client, router } = setup({ settings: settingsFixture });
    await screen.findByText("Accueil de Tremplin");
    server.use(
      http.get(`${API}/settings`, () =>
        HttpResponse.json(
          { error: { code: "internal_error", message: "Panne.", details: null } },
          { status: 500 },
        ),
      ),
    );
    await act(() => client.refetchQueries({ queryKey: ["settings"] }));
    expect(screen.getByText("Accueil de Tremplin")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(router.state.location.pathname).toBe("/");
  });

  it("lets an onboarded account open /welcome by hand, without sending it away", async () => {
    const { router, visited } = setup({ settings: settingsFixture }, "/welcome");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Tremplin's services" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/welcome");
    expect(visited).toEqual(["/welcome"]);
  });

  it("does not take the focus when the gate simply opens", async () => {
    setup({ settings: settingsFixture });
    expect(await screen.findByText("Accueil de Tremplin")).not.toHaveFocus();
  });
});
