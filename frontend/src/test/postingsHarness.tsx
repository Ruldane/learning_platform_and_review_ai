import { waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect } from "vitest";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { postingsApi } from "./postingsApi";
import { renderRoutes } from "./renderRoutes";
import { server } from "./server";

/**
 * Monte la page d'une offre (`p1`) avec les routes de `postingsApi` et des faux sockets, plus les
 * pages où ses liens mènent.
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
      { path: "/candidatures/:applicationId", element: <p>Application details</p> },
      {
        path: "/apprendre/programme/:programId/replanification",
        element: <p>Replan</p>,
      },
      { path: "/apprendre/objectifs", element: <p>Goals</p> },
    ],
    "/career/postings/p1",
  );
  return { ...view, ...postings, sockets };
}

/** Attend l'ouverture du flux de l'analyse (`a1`) et le branche. */
export async function openAnalysisStream(sockets: FakeSocketServer) {
  const streams = () => sockets.sockets.filter((s) => s.url.includes("/sessions/a1/stream"));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
