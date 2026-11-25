import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router";
import { onboardingApi } from "@/test/onboardingApi";
import { createQueryWrapper, createTestQueryClient } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { apiKeysFixture, modelsFixture, settingsFixture } from "../../fixtures";
import { OnboardingGate } from "../../OnboardingGate";
import { WelcomePage } from "./WelcomePage";

/** A new account: the first run is not done. */
export const fresh = { ...settingsFixture, onboarding_done: false };
export const noKey = apiKeysFixture.map((key) => ({ ...key, source: null, last4: null }));
/** Brave is in the back end's key list, but it is not a model provider. */
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
  "Tremplin's services",
  "What leaves your machine",
  "Your API key",
  "Your CV",
  "Your available time",
];
export const WEEKDAY = "Minutes per day, Monday to Friday";

/** The page behind the first-run gate, with a home page and a settings page. */
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
          { path: "settings", element: <p>Réglages</p> },
          { path: "welcome", element: <WelcomePage /> },
        ],
      },
    ],
    { initialEntries: [{ pathname: "/welcome", state }] },
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
export const next = (name: string | RegExp = /^(Next|Later|Skip|Finish)$/) =>
  screen.getByRole("button", { name });
export const skipAll = () => screen.getByRole("button", { name: "Skip the welcome" });
export const field = (label: string) => screen.getByLabelText(label);
export const finish = () => screen.getByRole("button", { name: "Finish" });

/** Advances to step `step` (from 1) with the advance button. */
export async function goTo(user: User, step: number) {
  await title(TITLES[0]!);
  for (let current = 1; current < step; current += 1) {
    await user.click(next());
    await title(TITLES[current]!);
  }
}

export const pdf = (name = "cv.pdf") => new File(["%PDF-1.4"], name, { type: "application/pdf" });
