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

/** A plan version as the back returns it (`PlanVersionOut`): one pending proposal. */
export const versionOut = (over: Record<string, unknown> = {}) => ({
  version: 2,
  kind: "replan",
  status: "pending",
  reason: "Deux semaines de suite en retard.",
  created_at: "2026-11-16T10:00:00Z",
  accepted_at: null,
  session_id: "s9",
  review: "Tu as fait 3 tâches sur 8 cette semaine.",
  diff: {
    added: ["Web / Réviser les verbes"],
    removed: ["Web / Vidéo bonus"],
    moved: [{ task: "Web / Lire le chapitre 1", before: "2026-11-16", after: "2026-11-18" }],
    weeks_before: 3,
    weeks_after: 3,
  },
  week_loads: [
    { rank: 1, start_date: "2026-11-16", before: 600, after: 540, cap: 714 },
    { rank: 2, start_date: "2026-11-23", before: 700, after: 714, cap: 714 },
  ],
  ...over,
});

/** The first version of a program: its construction, accepted. */
export const buildVersion = () =>
  versionOut({
    version: 1,
    kind: "build",
    status: "accepted",
    reason: "Programme validé.",
    accepted_at: "2026-11-10T10:00:00Z",
    session_id: null,
    review: null,
    diff: null,
    week_loads: [],
  });

/** The replanning session of program `p1` waiting for an answer. */
export const waitingSession = (id = "s9") =>
  sessionOut(id, "waiting_user", { graph: "replan", subject_type: "program", subject_id: "p1" });

interface ReplanApi {
  versions?: Record<string, unknown>[];
  /** Replannings waiting for an answer. */
  waiting?: Record<string, unknown>[];
  versionsReply?: () => Response;
}

/** Screen reads: plan history, pending replannings, status of session `s9`. */
export function replanApi(api: ReplanApi = {}) {
  const state = { versions: api.versions ?? [buildVersion()], waiting: api.waiting ?? [] };
  const handlers = [
    http.get(
      `${API}/programs/p1/versions`,
      () => api.versionsReply?.() ?? HttpResponse.json(state.versions),
    ),
    http.get(`${API}/sessions`, () => HttpResponse.json(state.waiting)),
    http.get(`${API}/sessions/s9`, () =>
      HttpResponse.json(
        sessionOut("s9", "waiting_user", {
          graph: "replan",
          subject_type: "program",
          subject_id: "p1",
        }),
      ),
    ),
  ];
  return { state, handlers };
}

/** Mounts the replanning screen of program `p1` with its reads and fake sockets. */
export function renderReplan(
  makePage: (createSocket: FakeSocketServer["factory"]) => ReactElement,
  api: ReplanApi = {},
) {
  const sockets = createFakeSocketServer();
  const replan = replanApi(api);
  server.use(...replan.handlers);
  const router = createMemoryRouter(
    [
      {
        path: "/learn/programs/:programId/replan",
        element: makePage(sockets.factory),
      },
      { path: "/learn/programs/:programId", element: <p>Programme</p> },
    ],
    { initialEntries: ["/learn/programs/p1/replan"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { fake: sockets, state: replan.state, router, user: userEvent.setup() };
}

/** Waits for session `s9`'s stream to open and plugs into it. */
export async function openReplanStream(fake: FakeSocketServer) {
  const streams = () => fake.sockets.filter((s) => s.url.includes("/sessions/s9/stream"));
  await waitFor(() => expect(streams()).toHaveLength(1));
  return streams()[0]!.open();
}
