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

const ROUTE = "/learn/goals/:goalId/council";

/**
 * Mounts the Council page (`makePage` receives the fake-socket factory) on objective `g1` with
 * the REST reads of `councilApi`. Returns the fake sockets, the API's editable state and a
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
    initialEntries: ["/learn/goals/g1/council"],
  });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake: sockets, state: council.state, user: userEvent.setup() };
}

/** The sockets open on this session's stream. */
export const socketsOf = (fake: FakeSocketServer, session: string) =>
  fake.sockets.filter((s) => s.url.includes(`/sessions/${session}/stream`));

/** Waits for the Council stream (`c1`) to open and plugs into it. */
export async function openCouncil(fake: FakeSocketServer) {
  await waitFor(() => expect(socketsOf(fake, "c1")).toHaveLength(1));
  return socketsOf(fake, "c1")[0]!.open();
}

/** Records the bodies received by a back POST route and answers `status` with `response`. */
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

/** The back's error body. */
export const apiError = (code: string, message: string, details: unknown = null) => ({
  error: { code, message, details },
});
