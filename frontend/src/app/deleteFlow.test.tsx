import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { DataPage } from "@/features/account/pages/DataPage";
import { settingsFixture } from "@/features/settings/fixtures";
import { OnboardingGate } from "@/features/settings/OnboardingGate";
import { WelcomePage } from "@/features/settings/pages/WelcomePage";
import { authApi, localMe } from "@/test/authApi";
import { API } from "@/test/councilApi";
import { onboardingApi } from "@/test/onboardingApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";

describe("« Tout supprimer » avec la porte du premier lancement", () => {
  it("returns to the welcome page with a notice after local account deletion", async () => {
    const api = onboardingApi({ settings: settingsFixture });
    server.use(
      // La suppression remet les réglages à zéro : le back les recrée au prochain `GET`.
      http.post(`${API}/account/delete`, () => {
        api.state.settings = { ...settingsFixture, onboarding_done: false, availability: null };
        return new HttpResponse(null, { status: 204 });
      }),
      ...api.handlers,
      ...authApi({ me: localMe }).handlers,
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 15_000 } },
    });
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
            { path: "settings/data", element: <DataPage /> },
            { path: "welcome", element: <WelcomePage /> },
          ],
        },
      ],
      { initialEntries: ["/settings/data"] },
    );
    const Wrapper = createQueryWrapper(client);
    render(
      <Wrapper>
        <RouterProvider router={router} />
      </Wrapper>,
    );
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Tape SUPPRIMER pour confirmer"), "SUPPRIMER");
    await user.click(screen.getByRole("button", { name: "Tout supprimer" }));

    expect(
      await screen.findByRole("heading", { level: 1, name: "Les services de Tremplin" }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/welcome");
    expect(
      screen.getByText("Tes données ont été supprimées : Tremplin repart de zéro."),
    ).toBeVisible();
    // Les réglages d'avant ne sont plus là : la porte les a relus, et le premier lancement a la main.
    expect(api.reads.settings).toBe(2);
    expect(client.getQueryData(["settings"])).toMatchObject({ onboarding_done: false });
  });
});
