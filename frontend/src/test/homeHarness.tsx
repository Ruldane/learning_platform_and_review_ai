import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { homeApi, type HomeApiOptions } from "./homeApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** The pages the home links lead to: landmarks, to check that we arrive there. */
const LANDINGS = [
  { path: "/study/session", element: <p>{"Page de la session d'étude"}</p> },
  { path: "/study/reviews", element: <p>Page des révisions</p> },
  { path: "/career/postings", element: <p>Page des offres</p> },
  { path: "/learn/goals", element: <p>Page des objectifs</p> },
  { path: "/applications/:applicationId", element: <p>Page de la fiche</p> },
];

/**
 * Mounts home at `/` (`makeUi` receives the fake-socket factory) with the brief and the feed in
 * memory from `homeApi`; the pages its links lead to are landmarks.
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

/** Waits for session `id`'s stream to open and plugs into it. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
