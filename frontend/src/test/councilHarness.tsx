import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { expect } from "vitest";
import { API, councilApi } from "./councilApi";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { createQueryWrapper } from "./queryWrapper";
import { server } from "./server";

const ROUTE = "/apprendre/objectifs/:goalId/conseil";

/**
 * Monte la page du Conseil (`makePage` reçoit la fabrique de faux sockets) sur l'objectif `g1` avec
 * les lectures REST de `councilApi`. Renvoie les faux sockets, l'état modifiable de l'API et un
 * `userEvent`.
 */
export function renderCouncil(
  makePage: (createSocket: FakeSocketServer["factory"]) => ReactElement,
  api: Parameters<typeof councilApi>[0] = {},
) {
  const sockets = createFakeSocketServer();
  const council = councilApi(api);
  server.use(...council.handlers);
  const router = createMemoryRouter([{ path: ROUTE, element: makePage(sockets.factory) }], {
    initialEntries: ["/apprendre/objectifs/g1/conseil"],
  });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake: sockets, state: council.state, user: userEvent.setup() };
}

/** Les sockets ouverts sur le flux de cette session. */
export const socketsOf = (fake: FakeSocketServer, session: string) =>
  fake.sockets.filter((s) => s.url.includes(`/sessions/${session}/stream`));

/** Attend l'ouverture du flux du Conseil (`c1`) et le branche. */
export async function openCouncil(fake: FakeSocketServer) {
  await waitFor(() => expect(socketsOf(fake, "c1")).toHaveLength(1));
  return socketsOf(fake, "c1")[0]!.open();
}

/** Enregistre les corps reçus par une route POST du back et répond `status` avec `response`. */
export function recordPosts(path: string, status = 202, response: Record<string, unknown> = {}) {
  const bodies: unknown[] = [];
  server.use(
    http.post(`${API}${path}`, async ({ request }) => {
      bodies.push(await request.json().catch(() => null));
      return HttpResponse.json(response, { status });
    }),
  );
  return bodies;
}

/** Corps d'erreur du back. */
export const apiError = (code: string, message: string, details: unknown = null) => ({
  error: { code, message, details },
});
