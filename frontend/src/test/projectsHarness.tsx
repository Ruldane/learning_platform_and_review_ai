import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { projectsApi, type ProjectsApiOptions } from "./projectsApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** The feature's two pages, as the manifest mounts them. */
export interface ProjectPages {
  portfolio: ReactElement;
  project: ReactElement;
}

/** The pages the Portfolio links lead to: landmarks, to check that we arrive there. */
const LANDINGS = [
  { path: "/skills", element: <p>Page de la carte des compétences</p> },
  { path: "/career/profile", element: <p>Page du profil maître</p> },
];

/**
 * Mounts the Portfolio and a project's page (`makeUi` receives the fake-socket factory) on their
 * production routes, at `path`, with the in-memory projects of `projectsApi`.
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

/** Waits for session `id`'s stream to open and plugs into it. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
