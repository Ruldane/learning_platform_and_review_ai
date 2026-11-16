import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { homeApi, type HomeApiOptions } from "./homeApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** Les pages où les liens de l'accueil mènent : des repères, pour vérifier qu'on y arrive. */
const LANDINGS = [
  { path: "/etudier/session", element: <p>{"Page de la session d'étude"}</p> },
  { path: "/etudier/revisions", element: <p>Page des révisions</p> },
  { path: "/carriere/offres", element: <p>Page des offres</p> },
  { path: "/apprendre/objectifs", element: <p>Page des objectifs</p> },
  { path: "/candidatures/:applicationId", element: <p>Page de la fiche</p> },
];

/**
 * Monte l'accueil à `/` (`makeUi` reçoit la fabrique de faux sockets) avec le brief et le fil en
 * mémoire de `homeApi` ; les pages où ses liens mènent sont des repères.
 */
export function renderHome(
  makeUi: (createSocket: FakeSocketServer["factory"]) => ReactElement,
  api: HomeApiOptions = {},
) {
  const sockets = createFakeSocketServer();
  const backend = homeApi(api);
  server.use(...backend.handlers);
  const view = renderRoutes([{ path: "/", element: makeUi(sockets.factory) }, ...LANDINGS], "/");
  return { ...view, ...backend, sockets };
}

/** Attend l'ouverture du flux de la session `id` et le branche. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
