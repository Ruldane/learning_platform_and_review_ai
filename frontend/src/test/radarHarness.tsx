import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { radarApi, type RadarApiOptions } from "./radarApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/**
 * Monte la page du radar à `path` (`makeUi` reçoit la fabrique de faux sockets) sur ses deux routes
 * (`/career/radar` et `/career/radar/:runId`, comme le manifeste) avec le radar en mémoire.
 */
export function renderRadar(
  makeUi: (createSocket: FakeSocketServer["factory"]) => ReactElement,
  api: RadarApiOptions = {},
  path = "/career/radar",
) {
  const sockets = createFakeSocketServer();
  const backend = radarApi(api);
  server.use(...backend.handlers);
  const view = renderRoutes(
    [
      { path: "/career/radar", element: makeUi(sockets.factory) },
      { path: "/career/radar/:runId", element: makeUi(sockets.factory) },
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
