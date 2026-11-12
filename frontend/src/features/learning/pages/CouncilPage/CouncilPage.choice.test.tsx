import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { API, proposalOut, sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { apiError, openCouncil, recordPosts, renderCouncil } from "@/test/councilHarness";
import type { FakeSocketServer } from "@/test/fakeSocket";
import { server } from "@/test/server";
import { CouncilPage } from "./CouncilPage";

vi.mock(
  "@excalidraw/excalidraw",
  async () => (await import("@/shared/session-ui/Board/excalidrawMock")).module,
);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const proposals = [
  proposalOut("p1", 1, { board_id: "b1" }),
  proposalOut("p2", 2),
  proposalOut("p3", 3),
];
const anotherRound = { label: "Demander un autre tour", value: "another_round" };

const setup = (api: Parameters<typeof renderCouncil>[1] = {}) =>
  renderCouncil((createSocket) => <CouncilPage createSocket={createSocket} />, {
    proposals,
    status: "waiting_user",
    ...api,
  });

/** Le Conseil arrive aux propositions et pose la question du choix. */
function reachChoice(fake: FakeSocketServer, options = [anotherRound]) {
  const e = councilEvents();
  return openCouncil(fake).then((socket) =>
    socket.push(
      e.message("moderator-tour-3", "Tour 3"),
      e.proposalReady("p1", "Parcours 1"),
      e.interrupt("choose_path", "i2", { question: "Choisis un parcours.", options }),
    ),
  );
}

describe("CouncilPage : propositions et choix", () => {
  beforeEach(() => useSessionStore.getState().reset("c1"));
  afterEach(() => useSessionStore.getState().reset("c1"));

  it("opens the proposals when the council reaches them and chooses one", async () => {
    const chosen = recordPosts("/proposals/p2/choose", 202, {
      council_session_id: "c1",
      status: "running",
      already_chosen: false,
    });
    const { fake, user } = setup();
    await reachChoice(fake);
    const cards = await screen.findAllByRole("article", { name: /^Parcours/ });
    expect(cards).toHaveLength(3);
    expect(screen.getByRole("tab", { name: "Propositions", selected: true })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choisir « Parcours 2 »" }));
    await waitFor(() => expect(chosen).toEqual([{ mix_with: null }]));
  });

  it("mixes two proposals", async () => {
    const mixed = recordPosts("/proposals/p1/choose", 202, {
      council_session_id: "c1",
      status: "running",
      already_chosen: false,
    });
    const { fake, user } = setup();
    await reachChoice(fake);
    await user.click(await screen.findByRole("checkbox", { name: "Mélanger « Parcours 1 »" }));
    await user.click(screen.getByRole("checkbox", { name: "Mélanger « Parcours 3 »" }));
    await user.click(screen.getByRole("button", { name: "Mélanger ces deux parcours" }));
    await waitFor(() => expect(mixed).toEqual([{ mix_with: "p3" }]));
  });

  it("asks for another round by resuming the choice question", async () => {
    const resumed = recordPosts("/sessions/c1/resume", 202, sessionOut("c1", "running"));
    const { fake, user } = setup();
    await reachChoice(fake);
    await user.click(await screen.findByRole("button", { name: "Demander un autre tour" }));
    await waitFor(() => expect(resumed).toEqual([{ interrupt_id: "i2", value: "another_round" }]));
  });

  it("offers no other round at the round cap (the question has no option)", async () => {
    const { fake } = setup();
    await reachChoice(fake, []);
    expect(await screen.findByRole("button", { name: "Choisir « Parcours 1 »" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Demander un autre tour" })).toBeNull();
    expect(screen.getByRole("button", { name: "Mélanger ces deux parcours" })).toBeInTheDocument();
  });

  it("does not offer a free text field for the choice question", async () => {
    const { fake } = setup();
    await reachChoice(fake);
    await screen.findByRole("button", { name: "Voir les propositions" });
    expect(screen.queryByRole("textbox", { name: "Ta réponse" })).toBeNull();
  });

  it("keeps the choice closed while the debate is still running", async () => {
    const { fake, user } = setup({ status: "running" });
    const e = councilEvents();
    (await openCouncil(fake)).push(e.message("moderator-tour-1", "Tour 1"));
    await user.click(await screen.findByRole("tab", { name: "Propositions" }));
    const choose = await screen.findByRole("button", { name: "Choisir « Parcours 1 »" });
    expect(choose).toBeDisabled();
    expect(screen.getByText(/Tu pourras choisir quand/)).toBeInTheDocument();
  });

  it("reloads the proposals on each proposal.ready", async () => {
    const { fake, state, user } = setup({ proposals: [proposalOut("p1", 1)], status: "running" });
    const e = councilEvents();
    const socket = await openCouncil(fake);
    await user.click(await screen.findByRole("tab", { name: "Propositions" }));
    expect(await screen.findAllByRole("article", { name: /^Parcours/ })).toHaveLength(1);
    state.proposals = [proposalOut("p8", 1), proposalOut("p9", 2)];
    socket.push(e.proposalReady("p8", "Nouveau 1"));
    await waitFor(() =>
      expect(screen.getAllByRole("article", { name: /^Parcours/ })).toHaveLength(2),
    );
  });

  it("reads the proposals again and says so on proposal_outdated (409), without an alert", async () => {
    server.use(
      http.post(`${API}/proposals/p2/choose`, () =>
        HttpResponse.json(apiError("proposal_outdated", "Lot périmé."), { status: 409 }),
      ),
    );
    const { fake, state, user } = setup();
    await reachChoice(fake);
    await screen.findAllByRole("article", { name: /^Parcours/ });
    state.proposals = [proposalOut("p7", 1), proposalOut("p8", 2)];
    await user.click(screen.getByRole("button", { name: "Choisir « Parcours 2 »" }));
    expect(
      await screen.findByText("Ces propositions ne sont plus d'actualité : voici les dernières."),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByRole("article", { name: /^Parcours/ })).toHaveLength(2),
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("reads the session again and says so on council_not_waiting (409)", async () => {
    server.use(
      http.post(`${API}/proposals/p1/choose`, () =>
        HttpResponse.json(
          apiError("council_not_waiting", "Le Conseil n'attend pas.", { status: "running" }),
          { status: 409 },
        ),
      ),
    );
    const { fake, user } = setup();
    await reachChoice(fake);
    await screen.findAllByRole("article", { name: /^Parcours/ });
    // La relecture rend l'état du serveur, plus récent que ce que le direct avait montré.
    server.use(
      http.get(`${API}/sessions/c1`, () =>
        HttpResponse.json(
          sessionOut("c1", "running", { last_seq: 99, updated_at: "2026-11-12T11:00:00.000000Z" }),
        ),
      ),
    );
    await user.click(screen.getByRole("button", { name: "Choisir « Parcours 1 »" }));
    expect(
      await screen.findByText(
        /Le Conseil n'attend pas ton choix pour l'instant \(état : En cours\)/,
      ),
    ).toBeInTheDocument();
    // L'état relu rend la main : les choix se referment.
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Choisir « Parcours 1 »" })).toBeDisabled(),
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("tells that the start date was not changed on already_chosen", async () => {
    recordPosts("/proposals/p1/choose", 202, {
      council_session_id: "c1",
      status: "running",
      already_chosen: true,
    });
    const { fake, user } = setup();
    await reachChoice(fake);
    await user.click(await screen.findByRole("button", { name: "Choisir « Parcours 1 »" }));
    expect(await screen.findByText(/la date de début est restée la même/)).toBeInTheDocument();
  });

  it("shows another error as an alert and keeps the cards", async () => {
    server.use(
      http.post(`${API}/proposals/p1/choose`, () =>
        HttpResponse.json(apiError("invalid_mix", "Mélange impossible."), { status: 422 }),
      ),
    );
    const { fake, user } = setup();
    await reachChoice(fake);
    await user.click(await screen.findByRole("button", { name: "Choisir « Parcours 1 »" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Mélange impossible.");
    expect(screen.getAllByRole("article", { name: /^Parcours/ })).toHaveLength(3);
  });

  it("offers « Réessayer » when the proposals cannot be read", async () => {
    let calls = 0;
    const { fake, user } = setup();
    server.use(
      http.get(`${API}/goals/g1/proposals`, () => {
        calls += 1;
        return calls === 1 ? HttpResponse.json({}, { status: 500 }) : HttpResponse.json(proposals);
      }),
    );
    await reachChoice(fake);
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(await screen.findAllByRole("article", { name: /^Parcours/ })).toHaveLength(3);
  });
});
