import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { postingsApi } from "./postingsApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/**
 * Mounts a posting's page (`p1`) with the routes of `postingsApi` and fake sockets, plus the
 * pages its links lead to.
 */
export function renderPosting(
  makePage: (createSocket: FakeSocketServer["factory"]) => ReactElement,
  api: Parameters<typeof postingsApi>[0] = {},
) {
  const sockets = createFakeSocketServer();
  const postings = postingsApi(api);
  server.use(...postings.handlers);
  const view = renderRoutes(
    [
      { path: "/career/postings/:postingId", element: makePage(sockets.factory) },
      { path: "/career/postings", element: <p>Postings list</p> },
      { path: "/applications/:applicationId", element: <p>Application details</p> },
      {
        path: "/learn/programs/:programId/replan",
        element: <p>Replan</p>,
      },
      { path: "/learn/goals", element: <p>Goals</p> },
    ],
    "/career/postings/p1",
  );
  return { ...view, ...postings, sockets };
}

/** Waits for the analysis stream (`a1`) to open and plugs into it. */
export async function openAnalysisStream(sockets: FakeSocketServer) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes("/sessions/a1/stream"));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
