import { waitFor } from "@testing-library/react";
import type { RouteObject } from "react-router";
import { expect } from "vitest";
import { applicationsApi, type ApplicationsApiOptions } from "./applicationsApi";
import type { FakeSocketServer } from "./fakeSocket";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/** The pages application links lead to: landmarks, to check that we arrive there. */
const LANDINGS: RouteObject[] = [
  { path: "/career/cv/versions", element: <p>Page des versions de CV</p> },
  { path: "/career/postings/:postingId", element: <p>{"Page de l'offre"}</p> },
];

/**
 * Mounts `routes` (the feature manifest's: the drawer is a child of tracking, at
 * `path`) with the in-memory routes of `applicationsApi`; pages of other tasks are
 * landmarks. Returns the router, a `userEvent`, the bodies received (`state`) and the data
 * (`rows`, `reminders`) that the test can change.
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

/** Waits for session `id`'s stream to open and plugs into it. */
export async function openStream(sockets: FakeSocketServer, id: string) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes(`/sessions/${id}/stream`));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
