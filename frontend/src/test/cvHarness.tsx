import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import type { Location } from "react-router";
import { expect } from "vitest";
import { cvApi } from "./cvApi";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** Les pages où les liens du CV mènent, pour vérifier qu'on y arrive. */
const LANDINGS = [
  { path: "/carriere/profil", element: <p>Page du profil</p> },
  { path: "/carriere/cv", element: <p>Page des modèles</p> },
  { path: "/carriere/cv/versions", element: <p>Page des versions</p> },
  { path: "/carriere/cv/modeles/:templateId", element: <p>Page du modèle</p> },
  { path: "/carriere/cv/revues/:reviewId", element: <p>Page de la revue</p> },
  { path: "/carriere/offres", element: <p>Liste des offres</p> },
  { path: "/carriere/offres/:postingId", element: <p>{"Page de l'offre"}</p> },
  { path: "/reglages/modeles", element: <p>Réglages des modèles</p> },
];

/**
 * Monte une page du CV à `path` avec les routes de `cvApi` et des faux sockets ; les pages où ses
 * liens mènent sont des repères. `route` est le motif de la page (`/carriere/cv/revues/:reviewId`).
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

/** Attend l'ouverture du flux de la session `id` et le branche. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
