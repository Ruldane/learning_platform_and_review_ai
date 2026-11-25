import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { createMemoryRouter, Outlet, RouterProvider, useLocation } from "react-router";
import { authManifest } from "./manifest";
import { SessionGate } from "./SessionGate";

/** Test layout page: it writes its path, to follow redirects. */
function Where() {
  return <p>{`Chemin : ${useLocation().pathname}`}</p>;
}

/**
 * Mounts the `auth` feature alone: its public routes, and a `/` root behind the gate with
 * `home` as content. The query cache keeps its default lifetime and its 15 s freshness
 * (as in the app): a redirect test must not depend on a cache just emptied.
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
  // One entry per path change: « une seule redirection » is counted here.
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
