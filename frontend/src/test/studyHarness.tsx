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
 * Monte la page de la session d'étude `st1` (`makePage` reçoit la fabrique de faux sockets) avec
 * les lectures REST de `studyApi`. Une route `/etudier/session` d'arrivée dit où l'on est allé.
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
      { path: "/etudier/session/:studyId", element: makePage(sockets.factory) },
      { path: "/etudier/session", element: <p>Départ de la session</p> },
      { path: "/etudier/revisions", element: <p>Révisions</p> },
    ],
    { initialEntries: ["/etudier/session/st1"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake: sockets, state: study.state, router, user: userEvent.setup() };
}

/** Attend l'ouverture du flux de la session d'agents `s1` et le branche. */
export async function openStudyStream(fake: FakeSocketServer) {
  const streams = () => fake.sockets.filter((s) => s.url.includes("/sessions/s1/stream"));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}

/** Enregistre les corps reçus par une route PATCH du back et répond `status` avec `response`. */
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
