import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { createMemoryRouter, Outlet, RouterProvider, useLocation } from "react-router";
import { authManifest } from "./manifest";
import { SessionGate } from "./SessionGate";

/** Page de la mise en page de test : elle écrit son chemin, pour suivre les redirections. */
function Where() {
  return <p>{`Chemin : ${useLocation().pathname}`}</p>;
}

/**
 * Monte la feature `auth` seule : ses routes publiques, et une racine `/` derrière la porte avec
 * `home` en contenu. Le cache de requêtes garde sa durée de vie par défaut et sa fraîcheur de 15 s
 * (comme l’application) : un test de redirection ne doit pas dépendre d'un cache vidé à l'instant.
 */
export function renderAuth(initial: string, home: ReactNode = <Where />) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 15_000 } },
  });
  const router = createMemoryRouter(
    [
      ...(authManifest.publicRoutes ?? []),
      {
        path: "/",
        element: (
          <SessionGate>
            <Outlet />
          </SessionGate>
        ),
        children: [
          { index: true, element: home },
          { path: "*", element: home },
        ],
      },
    ],
    { initialEntries: [initial] },
  );
  // Une entrée par changement de chemin : « une seule redirection » se compte ici.
  const visited: string[] = [router.state.location.pathname];
  router.subscribe((state) => {
    if (visited[visited.length - 1] !== state.location.pathname) {
      visited.push(state.location.pathname);
    }
  });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router, client, visited, user: userEvent.setup() };
}
