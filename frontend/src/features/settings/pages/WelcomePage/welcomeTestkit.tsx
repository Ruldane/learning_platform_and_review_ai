import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router";
import { onboardingApi } from "@/test/onboardingApi";
import { createQueryWrapper, createTestQueryClient } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { apiKeysFixture, modelsFixture, settingsFixture } from "../../fixtures";
import { OnboardingGate } from "../../OnboardingGate";
import { WelcomePage } from "./WelcomePage";

/** Un compte neuf : le premier lancement n'est pas fait. */
export const fresh = { ...settingsFixture, onboarding_done: false };
export const noKey = apiKeysFixture.map((key) => ({ ...key, source: null, last4: null }));
/** Brave est dans la liste des clés du back, mais ce n'est pas un fournisseur de modèles. */
const braveEnv = {
  provider: "brave",
  label: "Brave Search",
  source: "env",
  last4: "abcd",
  readable: true,
  last_test_ok: null,
  last_tested_at: null,
};
export const withBraveOnly = [...noKey, braveEnv];
export const withEnvKey = apiKeysFixture.map((key) => ({
  ...key,
  source: key.provider === "openai" ? "env" : null,
}));

export const TITLES = [
  "Les services de Tremplin",
  "Ce qui sort de ta machine",
  "Ta clé d'API",
  "Ton CV",
  "Ton temps disponible",
];
export const WEEKDAY = "Minutes par jour, du lundi au vendredi";

/** La page derrière la porte du premier lancement, avec un accueil et une page de réglages. */
export function setup(over: Partial<Parameters<typeof onboardingApi>[0]> = {}, state?: unknown) {
  const api = onboardingApi({ settings: fresh, keys: noKey, models: modelsFixture, ...over });
  server.use(...api.handlers);
  const client = createTestQueryClient();
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
          { index: true, element: <p>Accueil de Tremplin</p> },
          { path: "reglages", element: <p>Réglages</p> },
          { path: "bienvenue", element: <WelcomePage /> },
        ],
      },
    ],
    { initialEntries: [{ pathname: "/bienvenue", state }] },
  );
  const Wrapper = createQueryWrapper(client);
  render(
    <Wrapper>
      <RouterProvider router={router} />
    </Wrapper>,
  );
  return { ...api, client, router, user: userEvent.setup() };
}

type User = ReturnType<typeof setup>["user"];
export const title = (name: string) => screen.findByRole("heading", { level: 1, name });
export const next = (name: string | RegExp = /^(Suivant|Plus tard|Passer|Terminer)$/) =>
  screen.getByRole("button", { name });
export const skipAll = () => screen.getByRole("button", { name: "Passer l'accueil" });
export const field = (label: string) => screen.getByLabelText(label);
export const finish = () => screen.getByRole("button", { name: "Terminer" });

/** Avance jusqu'à l'étape `step` (à partir de 1) par le bouton qui avance. */
export async function goTo(user: User, step: number) {
  await title(TITLES[0]!);
  for (let current = 1; current < step; current += 1) {
    await user.click(next());
    await title(TITLES[current]!);
  }
}

export const pdf = (name = "cv.pdf") => new File(["%PDF-1.4"], name, { type: "application/pdf" });
