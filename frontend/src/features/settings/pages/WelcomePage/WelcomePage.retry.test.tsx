import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { onboardingApi } from "@/test/onboardingApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { fresh, TITLES } from "./welcomeTestkit";
import { WelcomePage } from "./WelcomePage";

describe("WelcomePage without its gate", () => {
  it("says the settings cannot be read, and after Réessayer the title has the focus", async () => {
    const api = onboardingApi({ settings: fresh, settingsFailures: 1 });
    server.use(...api.handlers);
    const { user } = renderRoutes([{ path: "/bienvenue", element: <WelcomePage /> }], "/bienvenue");
    expect(await screen.findByRole("alert")).toHaveTextContent("Le serveur a échoué.");
    expect(screen.queryByRole("button", { name: "Passer l'accueil" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    const heading = await screen.findByRole("heading", { level: 1, name: TITLES[0]! });
    await waitFor(() => expect(heading).toHaveFocus());
  });
});
