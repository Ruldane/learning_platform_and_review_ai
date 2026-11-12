import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { API, boardOut, goalOut, proposalOut, sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import {
  apiError,
  openCouncil,
  recordPosts,
  renderCouncil,
  socketsOf,
} from "@/test/councilHarness";
import { server } from "@/test/server";
import { CouncilPage } from "./CouncilPage";

vi.mock(
  "@excalidraw/excalidraw",
  async () => (await import("@/shared/session-ui/Board/excalidrawMock")).module,
);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const RETRY = "Relancer le Conseil";
const SESSIONS = ["c1", "c2", "pr1", "pr2"];

const setup = (api: Parameters<typeof renderCouncil>[1] = {}) =>
  renderCouncil((createSocket) => <CouncilPage createSocket={createSocket} />, api);

/** Le Conseil `c1` a échoué : le direct le dit. */
async function failCouncil(fake: Parameters<typeof openCouncil>[0]) {
  const e = councilEvents("c1");
  (await openCouncil(fake)).push(e.message("moderator-tour-1", "Tour 1"), e.failed());
}

describe("CouncilPage : relances", () => {
  beforeEach(() => SESSIONS.forEach((id) => useSessionStore.getState().reset(id)));
  afterEach(() => SESSIONS.forEach((id) => useSessionStore.getState().reset(id)));

  it("relaunches a failed council and follows the new session, without the old boards", async () => {
    const { fake, state, user } = setup({
      status: "failed",
      boards: [boardOut("b1", { session_id: "c1" })],
      proposals: [proposalOut("p1", 1)],
    });
    const relaunched = recordPosts("/goals/g1/council", 202, {
      goal: goalOut({ council_session_id: "c2" }),
      session_id: "c2",
    });
    server.use(
      http.get(`${API}/sessions/c2`, () => HttpResponse.json(sessionOut("c2", "running"))),
    );
    await failCouncil(fake);
    expect(await screen.findByRole("button", { name: /Carte du domaine/ })).toBeInTheDocument();

    // Le back rend encore les tableaux de l'ancien Conseil ; les propositions, plus aucune.
    state.goal = goalOut({ council_session_id: "c2" });
    state.proposals = [];
    await user.click(await screen.findByRole("button", { name: RETRY }));
    await waitFor(() => expect(relaunched).toHaveLength(1));
    await waitFor(() => expect(socketsOf(fake, "c2")).toHaveLength(1));
    socketsOf(fake, "c2")[0]!.open();

    expect(await screen.findByText("Le Scribe n'a encore rien dessiné.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Carte du domaine/ })).toBeNull();
    expect(screen.queryByRole("button", { name: RETRY })).toBeNull();
    await user.click(screen.getByRole("tab", { name: "Propositions" }));
    expect(
      await screen.findByText("Aucune proposition pour l'instant : l'équipe y travaille."),
    ).toBeInTheDocument();
  });

  it("does not offer the relaunch while the council is running", async () => {
    const { fake } = setup({ status: "running" });
    const e = councilEvents("c1");
    (await openCouncil(fake)).push(e.message("moderator-tour-1", "Tour 1"));
    await screen.findByText("Tour 1 / 4");
    expect(screen.queryByRole("button", { name: RETRY })).toBeNull();
  });

  it.each([
    [
      "council_not_failed",
      { status: "running" },
      "Le Conseil n'est pas en échec (état : En cours) : l'état a été relu.",
    ],
    [
      "goal_already_chosen",
      null,
      "Un programme est déjà lancé pour cet objectif : le Conseil ne peut plus être relancé. L'état a été relu.",
    ],
  ])("says so on %s (409) and reads the state again", async (code, details, text) => {
    let goalReads = 0;
    const { fake, user } = setup({
      status: "failed",
      goalReply: () => {
        goalReads += 1;
        return HttpResponse.json(goalOut());
      },
    });
    server.use(
      http.post(`${API}/goals/g1/council`, () =>
        HttpResponse.json(apiError(code, "Refusé.", details), { status: 409 }),
      ),
    );
    await failCouncil(fake);
    const reads = goalReads;
    await user.click(await screen.findByRole("button", { name: RETRY }));
    expect(await screen.findByText(text)).toBeInTheDocument();
    await waitFor(() => expect(goalReads).toBeGreaterThan(reads));
  });

  it("retries a failed program with the same choice and follows the new session", async () => {
    const { fake, state, user } = setup({
      goal: goalOut({ status: "chosen", program_session_id: "pr1" }),
      status: "completed",
      proposals: [proposalOut("p1", 1, { chosen: true }), proposalOut("p2", 2)],
    });
    server.use(
      http.get(`${API}/sessions/pr1`, () =>
        HttpResponse.json(sessionOut("pr1", "failed", { graph: "program_builder" })),
      ),
      http.get(`${API}/sessions/pr2`, () =>
        HttpResponse.json(sessionOut("pr2", "running", { graph: "program_builder" })),
      ),
    );
    const chosen = recordPosts("/proposals/p1/choose", 202, {
      council_session_id: "c1",
      status: "completed",
      already_chosen: false,
    });
    const e = councilEvents("c1");
    (await openCouncil(fake)).push(e.message("moderator-choix", "Parcours choisi"), e.completed());
    await waitFor(() => expect(socketsOf(fake, "pr1")).toHaveLength(1));
    socketsOf(fake, "pr1")[0]!.open().push(councilEvents("pr1").failed("Le Stratège a échoué."));

    expect(await screen.findByText("La préparation du programme a échoué.")).toBeInTheDocument();
    state.goal = goalOut({ status: "chosen", program_session_id: "pr2" });
    await user.click(screen.getByRole("button", { name: "Relancer la préparation du programme" }));
    await waitFor(() => expect(chosen).toEqual([{ mix_with: null }]));
    await waitFor(() => expect(socketsOf(fake, "pr2")).toHaveLength(1));
    expect(await screen.findByText("Le Stratège prépare ton programme…")).toBeInTheDocument();
  });

  it("retries a failed mix with both proposals", async () => {
    const { fake, user } = setup({
      goal: goalOut({ status: "chosen", program_session_id: "pr1" }),
      status: "completed",
      proposals: [
        proposalOut("p1", 1, { chosen: true }),
        proposalOut("p2", 2),
        proposalOut("p3", 3, { chosen: true }),
      ],
    });
    server.use(
      http.get(`${API}/sessions/pr1`, () =>
        HttpResponse.json(sessionOut("pr1", "failed", { graph: "program_builder" })),
      ),
    );
    const chosen = recordPosts("/proposals/p1/choose", 202, {
      council_session_id: "c1",
      status: "completed",
      already_chosen: false,
    });
    await openCouncil(fake);
    await waitFor(() => expect(socketsOf(fake, "pr1")).toHaveLength(1));
    socketsOf(fake, "pr1")[0]!.open().push(councilEvents("pr1").failed());
    await user.click(
      await screen.findByRole("button", { name: "Relancer la préparation du programme" }),
    );
    await waitFor(() => expect(chosen).toEqual([{ mix_with: "p3" }]));
  });
});
