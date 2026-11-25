import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { expect } from "vitest";
import { API } from "./councilApi";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { createQueryWrapper } from "./queryWrapper";
import { server } from "./server";
import { studyApi } from "./studyApi";

/**
 * Mounts the study session page `st1` (`makePage` receives the fake-socket factory) with
 * the REST reads of `studyApi`. An arrival route `/study/session` says where we went.
 */
export function renderStudySession(
  makePage: (createSocket: FakeSocketServer["factory"]) => ReactElement,
  api: Parameters<typeof studyApi>[0] = {},
) {
  const sockets = createFakeSocketServer();
  const study = studyApi(api);
  server.use(...study.handlers);
  const router = createMemoryRouter(
    [
      { path: "/study/session/:studyId", element: makePage(sockets.factory) },
      { path: "/study/session", element: <p>Départ de la session</p> },
      { path: "/study/reviews", element: <p>Révisions</p> },
    ],
    { initialEntries: ["/study/session/st1"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake: sockets, state: study.state, router, user: userEvent.setup() };
}

/** Waits for the agent session `s1`'s stream to open and plugs into it. */
export async function openStudyStream(fake: FakeSocketServer) {
  const streams = () => fake.sockets.filter((s) => s.url.includes("/sessions/s1/stream"));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}

/** Records the bodies received by a back PATCH route and answers `status` with `response`. */
export function recordPatches(path: string, status = 202, response: Record<string, unknown> = {}) {
  const bodies: unknown[] = [];
  server.use(
    http.patch(`${API}${path}`, async ({ request }) => {
      bodies.push(await request.json().catch(() => null));
      return HttpResponse.json(response, { status });
    }),
  );
  return bodies;
}
