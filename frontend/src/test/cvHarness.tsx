import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import type { Location } from "react-router";
import { expect } from "vitest";
import { cvApi } from "./cvApi";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** The pages the CV links lead to, to check that we arrive there. */
const LANDINGS = [
  { path: "/career/profile", element: <p>Page du profil</p> },
  { path: "/career/cv", element: <p>Page des modèles</p> },
  { path: "/career/cv/versions", element: <p>Page des versions</p> },
  { path: "/career/cv/templates/:templateId", element: <p>Page du modèle</p> },
  { path: "/career/cv/reviews/:reviewId", element: <p>Page de la revue</p> },
  { path: "/career/postings", element: <p>Liste des offres</p> },
  { path: "/career/postings/:postingId", element: <p>{"Page de l'offre"}</p> },
  { path: "/settings/models", element: <p>Réglages des modèles</p> },
];

/**
 * Mounts a CV page at `path` with the routes of `cvApi` and fake sockets; the pages its
 * links lead to are landmarks. `route` is the page pattern (`/career/cv/reviews/:reviewId`).
 */
export function renderCv(
  route: string,
  path: string | Partial<Location>,
  makePage: (createSocket: FakeSocketServer["factory"]) => ReactElement,
  api: Parameters<typeof cvApi>[0] = {},
) {
  const sockets = createFakeSocketServer();
  const cv = cvApi(api);
  server.use(...cv.handlers);
  const pages = LANDINGS.filter((landing) => landing.path !== route);
  const view = renderRoutes([{ path: route, element: makePage(sockets.factory) }, ...pages], path);
  return { ...view, ...cv, sockets };
}

/** Waits for session `id`'s stream to open and plugs into it. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
