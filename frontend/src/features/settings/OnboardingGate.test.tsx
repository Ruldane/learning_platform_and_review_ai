import { screen, waitFor } from "@testing-library/react";
import { Outlet } from "react-router";
import { describe, expect, it } from "vitest";
import { onboardingApi } from "@/test/onboardingApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { settingsFixture } from "./fixtures";
import { OnboardingGate } from "./OnboardingGate";
import { WelcomePage } from "./pages/WelcomePage";

const fresh = { ...settingsFixture, onboarding_done: false };

function setup(over: Parameters<typeof onboardingApi>[0], at = "/") {
  const api = onboardingApi(over);
  server.use(...api.handlers);
  const view = renderRoutes(
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
          { path: "apprendre", element: <p>Apprendre</p> },
          { path: "bienvenue", element: <WelcomePage /> },
        ],
      },
    ],
    at,
  );
  // Une entrée par changement de chemin : « une seule redirection » se compte ici.
  const visited = [view.router.state.location.pathname];
  view.router.subscribe((state) => {
    if (visited[visited.length - 1] !== state.location.pathname) {
      visited.push(state.location.pathname);
    }
  });
  return { ...api, ...view, visited };
}

describe("OnboardingGate", () => {
  it("gate sends a new account to /bienvenue", async () => {
    const { router, visited } = setup({ settings: fresh }, "/apprendre");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Les services de Tremplin" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Apprendre")).toBeNull();
    expect(router.state.location.pathname).toBe("/bienvenue");
    // Un remplacement : « précédent » ne ramène pas à une porte qui renverrait aussitôt.
    expect(router.state.historyAction).toBe("REPLACE");
    expect(visited).toEqual(["/apprendre", "/bienvenue"]);
  });

  it("gate lets an onboarded account through", async () => {
    const { router, visited } = setup({ settings: settingsFixture }, "/apprendre");
    expect(await screen.findByText("Apprendre")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/apprendre");
    expect(visited).toEqual(["/apprendre"]);
  });

  it("does not send a new account away from /bienvenue, nor loop", async () => {
    const { visited } = setup({ settings: fresh }, "/bienvenue");
    await screen.findByRole("heading", { level: 1, name: "Les services de Tremplin" });
    expect(visited).toEqual(["/bienvenue"]);
  });

  it("keeps the layout away while the settings are read", async () => {
    const { reads } = setup({ settings: settingsFixture });
    expect(screen.getByRole("status")).toHaveTextContent("Préparation de ton espace");
    expect(screen.queryByText("Accueil de Tremplin")).toBeNull();
    await screen.findByText("Accueil de Tremplin");
    expect(reads.settings).toBe(1);
  });

  it("shows the failure, and a retry that hands the focus to the page content", async () => {
    const { user, reads } = setup({ settings: settingsFixture, settingsFailures: 1 });
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur a échoué.");
    expect(screen.queryByText("Accueil de Tremplin")).toBeNull();
    const retry = screen.getByRole("button", { name: "Réessayer" });
    retry.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("Accueil de Tremplin")).toHaveFocus();
    expect(reads.settings).toBe(2);
  });

  it("after a retry that leads to /bienvenue, the focus is the title of the step", async () => {
    const { user, router } = setup({ settings: fresh, settingsFailures: 1 });
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    const title = await screen.findByRole("heading", {
      level: 1,
      name: "Les services de Tremplin",
    });
    await waitFor(() => expect(title).toHaveFocus());
    expect(router.state.location.pathname).toBe("/bienvenue");
  });

  it("does not take the focus when the gate simply opens", async () => {
    setup({ settings: settingsFixture });
    expect(await screen.findByText("Accueil de Tremplin")).not.toHaveFocus();
  });
});
