import { waitFor } from "@testing-library/react";
import type { RouteObject } from "react-router";
import { expect } from "vitest";
import { applicationsApi, type ApplicationsApiOptions } from "./applicationsApi";
import type { FakeSocketServer } from "./fakeSocket";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** Les pages où les liens des candidatures mènent : des repères, pour vérifier qu'on y arrive. */
const LANDINGS: RouteObject[] = [
  { path: "/carriere/cv/versions", element: <p>Page des versions de CV</p> },
  { path: "/career/postings/:postingId", element: <p>{"Page de l'offre"}</p> },
];

/**
 * Monte `routes` (celles du manifeste de la feature : le tiroir est bien un enfant du suivi, à
 * `path`) avec les routes en mémoire de `applicationsApi` ; les pages des autres tâches sont des
 * repères. Renvoie le routeur, un `userEvent`, les corps reçus (`state`) et les données (`rows`,
 * `reminders`) que le test peut changer.
 */
export function renderApplications(
  routes: RouteObject[],
  path: string,
  api: ApplicationsApiOptions = {},
) {
  const backend = applicationsApi(api);
  server.use(...backend.handlers);
  const view = renderRoutes([{ path: "/", children: [...routes, ...LANDINGS] }], path);
  return { ...view, ...backend };
}

/** Attend l'ouverture du flux de la session `id` et le branche. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
