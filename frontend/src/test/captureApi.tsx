import { render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { expect } from "vitest";
import { API, sessionOut } from "./councilApi";
import { createFakeSocketServer, type FakeSocketServer } from "./fakeSocket";
import { createQueryWrapper } from "./queryWrapper";
import { server } from "./server";

/**
 * Monte la capture (`makeUi` reçoit la fabrique de faux sockets) dans un routeur en mémoire, avec
 * le statut de la session de capture `s5` et une page d'arrivée pour le journal.
 */
export function renderCapture(makeUi: (createSocket: FakeSocketServer["factory"]) => ReactElement) {
  const sockets = createFakeSocketServer();
  server.use(
    http.get(`${API}/sessions/s5`, () =>
      HttpResponse.json(
        sessionOut("s5", "running", { graph: "capture", subject_type: null, subject_id: null }),
      ),
    ),
  );
  const router = createMemoryRouter(
    [
      { path: "/", element: makeUi(sockets.factory) },
      { path: "/etudier/journal", element: <p>Page du journal</p> },
    ],
    { initialEntries: ["/"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake: sockets, router, user: userEvent.setup() };
}

/** Attend l'ouverture du flux de la session de capture `s5` et le branche. */
export async function openCaptureStream(fake: FakeSocketServer) {
  const streams = () => fake.sockets.filter((s) => s.url.includes("/sessions/s5/stream"));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}

/** Une entrée du journal telle que le back la rend (`JournalEntryOut`). */
export const entryOut = (id: string, over: Record<string, unknown> = {}) => ({
  id,
  kind: "capture",
  text: `Entrée ${id}`,
  occurred_on: "2026-11-17",
  created_at: "2026-11-17T10:00:00Z",
  links: { session_id: null, study_session_id: null, quiz_attempt_id: null, memory_item_id: null },
  ...over,
});
