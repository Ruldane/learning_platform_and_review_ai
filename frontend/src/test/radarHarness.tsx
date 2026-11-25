import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { radarApi, type RadarApiOptions } from "./radarApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/**
 * Mounts the radar page at `path` (`makeUi` receives the fake-socket factory) on its two routes
 * (`/career/radar` and `/career/radar/:runId`, as in the manifest) with the in-memory radar.
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

/** Waits for session `id`'s stream to open and plugs into it. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
