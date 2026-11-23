import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { accountApi } from "@/test/accountApi";
import { authApi, camille, localMe } from "@/test/authApi";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { DataPage } from "./DataPage";

/** « Mes données » en mode `local` ou `google`, avec la réponse voulue pour la suppression. */
export function setup(
  mode: "local" | "google",
  deleteOutcome: Parameters<typeof accountApi>[0] = {},
  auth: { meFails?: boolean } = {},
) {
  const account = accountApi(deleteOutcome);
  const authentication = authApi({ me: mode === "local" ? localMe : camille, ...auth });
  server.use(...account.handlers, ...authentication.handlers);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 15_000 } },
  });
  client.setQueryData(["settings"], { onboarding_done: true });
  client.setQueryData(["auth", "me"], mode === "local" ? localMe : camille);
  client.setQueryData(["goals"], [{ id: "g1" }]);
  const router = createMemoryRouter(
    [
      { path: "/reglages/donnees", element: <DataPage /> },
      { path: "/bienvenue", element: <p>Premier lancement</p> },
      { path: "/connexion", element: <p>Connexion</p> },
    ],
    { initialEntries: ["/reglages/donnees"] },
  );
  const Wrapper = createQueryWrapper(client);
  render(
    <Wrapper>
      <RouterProvider router={router} />
    </Wrapper>,
  );
  return { ...account, auth: authentication, client, router, user: userEvent.setup() };
}

export const word = () => screen.getByLabelText("Tape SUPPRIMER pour confirmer");
export const deleteButton = () =>
  screen.getByRole("button", { name: /^(Tout supprimer|Suppression en cours…)$/ });

export async function confirmAndDelete(user: ReturnType<typeof userEvent.setup>) {
  await user.type(word(), "SUPPRIMER");
  await user.click(screen.getByRole("button", { name: "Tout supprimer" }));
}
