import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { projectsApi, type ProjectsApiOptions } from "./projectsApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** Les deux pages de la feature, telles que le manifeste les monte. */
export interface ProjectPages {
  portfolio: ReactElement;
  project: ReactElement;
}

/** Les pages où les liens du Portfolio mènent : des repères, pour vérifier qu'on y arrive. */
const LANDINGS = [
  { path: "/skills", element: <p>Page de la carte des compétences</p> },
  { path: "/career/profile", element: <p>Page du profil maître</p> },
];

/**
 * Monte le Portfolio et la page d'un projet (`makeUi` reçoit la fabrique de faux sockets) sur leurs
 * routes de production, à `path`, avec les projets en mémoire de `projectsApi`.
 */
export function renderProjects(
  makeUi: (createSocket: FakeSocketServer["factory"]) => ProjectPages,
  api: ProjectsApiOptions = {},
  path = "/skills/portfolio",
) {
  const sockets = createFakeSocketServer();
  const backend = projectsApi(api);
  server.use(...backend.handlers);
  const pages = makeUi(sockets.factory);
  const view = renderRoutes(
    [
      { path: "/skills/portfolio", element: pages.portfolio },
      { path: "/skills/portfolio/:projectId", element: pages.project },
      ...LANDINGS,
    ],
    path,
  );
  return { ...view, ...backend, sockets };
}

/** Attend l'ouverture du flux de la session `id` et le branche. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
