import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { goalOut, sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { openCouncil, recordPosts, renderCouncil, socketsOf } from "@/test/councilHarness";
import { CouncilPage } from "./CouncilPage";

vi.mock(
  "@excalidraw/excalidraw",
  async () => (await import("@/shared/session-ui/Board/excalidrawMock")).module,
);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const setup = (api: Parameters<typeof renderCouncil>[1] = {}) =>
  renderCouncil((createSocket) => <CouncilPage createSocket={createSocket} />, api);

const socketOf = socketsOf;

const framingFields = [
  { id: "q1", label: "Quel type d'entreprise vises-tu ?", max_length: 2000, required: false },
  { id: "q2", label: "Quand veux-tu changer de poste ?", max_length: 2000, required: false },
];

describe("CouncilPage", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("c1");
    useSessionStore.getState().reset("pr1");
  });
  afterEach(() => {
    useSessionStore.getState().reset("c1");
    useSessionStore.getState().reset("pr1");
  });

  it("shows its heading and the goal at once, then opens the stream of the council session", async () => {
    const { fake } = setup();
    expect(screen.getByRole("heading", { name: "Conseil" })).toBeInTheDocument();
    expect(await screen.findByText("Devenir ingénieure data")).toBeInTheDocument();
    await waitFor(() => expect(socketOf(fake, "c1")).toHaveLength(1));
    expect(socketOf(fake, "c1")[0]!.url).toContain("/sessions/c1/stream?after_seq=0");
  });

  it("answers the framing questions: typed answers go with « Lancer la recherche »", async () => {
    const bodies = recordPosts("/sessions/c1/resume", 202, sessionOut("c1", "running"));
    const { fake, user } = setup({ status: "waiting_user" });
    const e = councilEvents();
    (await openCouncil(fake)).push(
      e.interrupt("framing", "i1", {
        question: "Réponds aux questions de cadrage.",
        options: [{ label: "Lancer la recherche", value: "go" }],
        fields: framingFields,
      }),
    );
    await user.type(
      await screen.findByLabelText("Quel type d'entreprise vises-tu ?"),
      "Une startup",
    );
    await user.click(screen.getByRole("button", { name: "Lancer la recherche" }));
    await waitFor(() =>
      expect(bodies).toEqual([{ interrupt_id: "i1", value: { answers: { q1: "Une startup" } } }]),
    );
  });

  it("launches the research with « go » when no field is filled", async () => {
    const bodies = recordPosts("/sessions/c1/resume", 202, sessionOut("c1", "running"));
    const { fake, user } = setup({ status: "waiting_user" });
    const e = councilEvents();
    (await openCouncil(fake)).push(
      e.interrupt("framing", "i1", {
        options: [{ label: "Lancer la recherche", value: "go" }],
        fields: framingFields,
      }),
    );
    await user.click(await screen.findByRole("button", { name: "Lancer la recherche" }));
    await waitFor(() => expect(bodies).toEqual([{ interrupt_id: "i1", value: "go" }]));
  });

  it("streams four agents, the board and the sources", async () => {
    const { fake, user } = setup();
    const e = councilEvents();
    const socket = await openCouncil(fake);
    socket.push(
      ...Array.from({ length: 8 }, (_, i) =>
        e.sourceFound({ source_id: `s${i}`, title: `Source ${i}`, url: `https://exemple.fr/${i}` }),
      ),
      e.message("moderator-tour-1", "Tour 1 : ordre de parole", "moderator"),
      e.message("strategist-positions", "Position du Stratège", "strategist"),
      e.message("skeptic-positions", "Position du Sceptique", "skeptic"),
      e.message("practitioner-positions", "Position du Praticien", "practitioner"),
      e.boardUpdate("b1", 1),
    );
    expect(await screen.findAllByRole("article")).toHaveLength(4);
    expect(screen.getByRole("tab", { name: "Tableau" })).toBeInTheDocument();
    expect(screen.getByText("Tour 1 / 3")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Sources" }));
    const kept = await screen.findByRole("region", { name: "Retenues" });
    expect(within(kept).getAllByRole("listitem")).toHaveLength(8);
  });

  it("keeps the composer active during the debate and sends messages and commands", async () => {
    const messages = recordPosts("/sessions/c1/message", 202, { id: "m", seq: 1 });
    const { fake, user } = setup();
    const e = councilEvents();
    (await openCouncil(fake)).push(e.message("moderator-tour-1", "Tour 1"));
    const field = await screen.findByLabelText("Ton message");
    expect(field).toBeEnabled();
    await user.type(field, "Peux-tu parler de Docker ?");
    await user.click(screen.getByRole("button", { name: "Envoyer" }));
    await waitFor(() => expect(messages).toEqual([{ text: "Peux-tu parler de Docker ?" }]));
    await user.click(screen.getByRole("button", { name: "Plus court" }));
    await waitFor(() => expect(messages.at(-1)).toEqual({ text: "", command: "shorter" }));
    await user.click(screen.getByRole("button", { name: "Passer aux propositions" }));
    await waitFor(() => expect(messages.at(-1)).toEqual({ text: "", command: "to_proposals" }));
  });

  it("closes the composer once the council is over", async () => {
    const { fake } = setup({ status: "completed" });
    const e = councilEvents();
    (await openCouncil(fake)).push(e.message("moderator-choix", "Parcours choisi"), e.completed());
    await waitFor(() => expect(screen.getByLabelText("Ton message")).toBeDisabled());
    expect(screen.getByRole("button", { name: "Plus court" })).toBeDisabled();
  });

  it("asks before cancelling, without a browser dialog", async () => {
    const cancelled = recordPosts("/sessions/c1/cancel", 202, sessionOut("c1", "cancelled"));
    const dialog = vi.spyOn(window, "confirm");
    const { fake, user } = setup();
    const e = councilEvents();
    (await openCouncil(fake)).push(e.message("moderator-tour-1", "Tour 1"));
    await user.click(await screen.findByRole("button", { name: "Annuler" }));
    expect(cancelled).toHaveLength(0);
    await user.click(screen.getByRole("button", { name: "Oui, arrêter" }));
    await waitFor(() => expect(cancelled).toHaveLength(1));
    expect(dialog).not.toHaveBeenCalled();
  });

  it("does not duplicate a node replayed after a restart (same ids published again)", async () => {
    const { fake, user } = setup();
    const e = councilEvents();
    const socket = await openCouncil(fake);
    socket.push(
      e.started("scribe"),
      e.message("scribe-positions", "Carte dessinée", "scribe"),
      e.boardUpdate("b1", 1),
      e.sourceFound({ source_id: "s1", title: "Une page", url: "https://exemple.fr/1" }),
    );
    // Redémarrage : le nœud repart (nouveaux seq) et republie les mêmes identifiants.
    socket.push(
      e.started("scribe"),
      e.message("scribe-positions", "Carte dessinée", "scribe"),
      e.boardUpdate("b1", 1),
      e.sourceFound({ source_id: "s1", title: "Une page", url: "https://exemple.fr/1" }),
    );
    expect(await screen.findAllByRole("article")).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /Carte du domaine/ })).toHaveLength(1);
    await user.click(screen.getByRole("tab", { name: "Sources" }));
    const kept = await screen.findByRole("region", { name: "Retenues" });
    expect(within(kept).getAllByRole("listitem")).toHaveLength(1);
  });

  it("keeps pages and practitioners apart in the sources, counts included", async () => {
    const { fake, user } = setup();
    const e = councilEvents();
    (await openCouncil(fake)).push(
      e.sourceFound({ source_id: "s1", title: "Une page" }),
      e.sourceFound({
        source_id: "p1",
        kind: "person",
        title: "Ada",
        role: "Ingénieure ML",
        verdict: null,
        score: null,
      }),
      e.sourceFound({
        source_id: "p2",
        kind: "person",
        title: "Bob",
        role: "Dev",
        verdict: null,
        score: null,
      }),
    );
    await user.click(await screen.findByRole("tab", { name: "Sources" }));
    const kept = await screen.findByRole("region", { name: "Retenues" });
    expect(within(kept).getAllByRole("listitem")).toHaveLength(1);
    expect(within(kept).queryByText("Ada")).toBeNull();
    const people = screen.getByRole("region", { name: "Praticiens repérés" });
    expect(within(people).getAllByRole("listitem")).toHaveLength(2);
  });

  it("shows an unknown goal as such", async () => {
    const missing = () =>
      HttpResponse.json(
        { error: { code: "goal_not_found", message: "Objectif introuvable.", details: null } },
        { status: 404 },
      );
    setup({ goalReply: missing });
    expect(await screen.findByText("Objectif introuvable")).toBeInTheDocument();
  });

  it("offers « Réessayer » when the goal cannot be read", async () => {
    let calls = 0;
    const { user } = setup({
      goalReply: () => {
        calls += 1;
        return calls === 1 ? HttpResponse.json({}, { status: 500 }) : HttpResponse.json(goalOut());
      },
    });
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Devenir ingénieure data")).toBeInTheDocument();
  });

  it("says when the council session cannot be found, with a way back", async () => {
    const { fake } = setup();
    await waitFor(() => expect(socketOf(fake, "c1")).toHaveLength(1));
    socketOf(fake, "c1")[0]!.open().drop(4404);
    expect(await screen.findByRole("alert")).toHaveTextContent("Cette session est introuvable.");
    expect(screen.getByRole("button", { name: "Retour aux objectifs" })).toBeInTheDocument();
  });
});
