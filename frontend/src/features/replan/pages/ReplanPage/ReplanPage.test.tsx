import { screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { councilEvents } from "@/test/councilEvents";
import { apiError, recordPosts } from "@/test/councilHarness";
import {
  buildVersion,
  openReplanStream,
  renderReplan,
  versionOut,
  waitingSession,
} from "@/test/replanApi";
import { ReplanPage } from "./ReplanPage";

vi.mock(
  "@excalidraw/excalidraw",
  async () => (await import("@/shared/session-ui/Board/excalidrawMock")).module,
);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const setup = (api: Parameters<typeof renderReplan>[1] = {}) =>
  renderReplan((createSocket) => <ReplanPage createSocket={createSocket} />, api);

const acceptQuestion = (e: ReturnType<typeof councilEvents>) =>
  e.interrupt("accept_replan", "i1", {
    question: "Voici le plan proposé, avant et après. L'accepter ?",
    options: [
      { value: "accept", label: "Accepter le nouveau plan" },
      { value: "refuse", label: "Garder le plan actuel" },
    ],
    fields: [{ id: "note", label: "Ce qu'il faut revoir", max_length: 2000, required: false }],
  });

const resumed = {
  id: "s9",
  graph: "replan",
  status: "running",
  last_seq: 0,
  pending_interrupt: null,
};

describe("ReplanPage", () => {
  beforeEach(() => useSessionStore.getState().reset("s9"));
  afterEach(() => useSessionStore.getState().reset("s9"));

  it("starts a replan with available hours", async () => {
    const posts = recordPosts("/programs/p1/replan", 202, { session_id: "s9" });
    const { user, fake } = setup();
    await user.type(
      await screen.findByLabelText("Heures pour toute la semaine (déjà faites comprises)"),
      "5",
    );
    await user.type(screen.getByLabelText("Un message pour le Stratège"), "Je suis malade lundi.");
    await user.click(screen.getByRole("button", { name: "Replanifier" }));
    await waitFor(() =>
      expect(posts).toEqual([{ available_minutes: 300, message: "Je suis malade lundi." }]),
    );
    const e = councilEvents("s9");
    (await openReplanStream(fake)).push(e.message("m1", "Je prépare ta semaine.", "strategist"));
    expect(await screen.findByText("Je prépare ta semaine.")).toBeInTheDocument();
  });

  it("says that the hours already done count (revue finale 5, C-m3)", async () => {
    setup();
    const field = await screen.findByLabelText(
      "Heures pour toute la semaine (déjà faites comprises)",
    );
    expect(field).toHaveAccessibleDescription(/y compris les heures déjà faites/);
  });

  it("refuses hours outside the contract without calling the back", async () => {
    const posts = recordPosts("/programs/p1/replan", 202, { session_id: "s9" });
    const { user } = setup();
    await user.type(
      await screen.findByLabelText("Heures pour toute la semaine (déjà faites comprises)"),
      "500",
    );
    await user.click(screen.getByRole("button", { name: "Replanifier" }));
    expect(await screen.findByText(/compris entre 1 et 168/)).toBeInTheDocument();
    expect(posts).toEqual([]);
  });

  it("follows the open session when a replan is already running (409 replan_open)", async () => {
    recordPosts(
      "/programs/p1/replan",
      409,
      apiError("replan_open", "Déjà en cours.", { session_id: "s9" }),
    );
    const { user, fake } = setup();
    await user.click(await screen.findByRole("button", { name: "Replanifier" }));
    const e = councilEvents("s9");
    (await openReplanStream(fake)).push(e.message("m1", "Reprenons.", "strategist"));
    expect(await screen.findByText("Reprenons.")).toBeInTheDocument();
    expect(screen.queryByText("Déjà en cours.")).toBeNull();
  });

  it("shows a refused start (draft program) inline and keeps the form", async () => {
    recordPosts("/programs/p1/replan", 409, apiError("program_not_validated", "Valide d'abord."));
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Replanifier" }));
    expect(await screen.findByText("Valide d'abord.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Replanifier" })).toBeEnabled();
  });

  it("shows before and after loads under the cap", async () => {
    setup({ versions: [versionOut(), buildVersion()], waiting: [waitingSession()] });
    const panel = await screen.findByRole("region", { name: "Proposition du Stratège" });
    const table = within(panel).getByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(within(rows[1]!).getByText("10 h")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("9 h")).toBeInTheDocument();
    expect(within(rows[1]!).getAllByText("11 h 54")).toHaveLength(1);
    expect(within(rows[1]!).getByText("Sous le plafond")).toBeInTheDocument();
    expect(within(rows[2]!).getByText("Au plafond")).toBeInTheDocument();
    expect(within(panel).getByText("Tu as fait 3 tâches sur 8 cette semaine.")).toBeInTheDocument();
    expect(within(panel).getByText("Réviser les verbes")).toBeInTheDocument();
    expect(within(panel).getByText("lun. 16 nov. → mer. 18 nov.")).toBeInTheDocument();
  });

  it("accepts the proposal through the interrupt", async () => {
    const resumes = recordPosts("/sessions/s9/resume", 202, {
      id: "s9",
      graph: "replan",
      status: "running",
      last_seq: 0,
      pending_interrupt: null,
    });
    const { user, fake } = setup({ versions: [versionOut()], waiting: [waitingSession()] });
    (await openReplanStream(fake)).push(acceptQuestion(councilEvents("s9")));
    await user.click(await screen.findByRole("button", { name: "Accepter le nouveau plan" }));
    await waitFor(() => expect(resumes).toEqual([{ interrupt_id: "i1", value: "accept" }]));
  });

  it("accepts with a note: the clicked button still decides (revue finale 5, C-I2)", async () => {
    const resumes = recordPosts("/sessions/s9/resume", 202, resumed);
    const { user, fake } = setup({ versions: [versionOut()], waiting: [waitingSession()] });
    (await openReplanStream(fake)).push(acceptQuestion(councilEvents("s9")));
    await user.type(await screen.findByLabelText("Ce qu'il faut revoir"), "Ok, garde le jeudi.");
    await user.click(screen.getByRole("button", { name: "Accepter le nouveau plan" }));
    await waitFor(() =>
      expect(resumes).toEqual([
        { interrupt_id: "i1", value: { action: "accept", note: "Ok, garde le jeudi." } },
      ]),
    );
  });

  it("keeps the current plan with a note", async () => {
    const resumes = recordPosts("/sessions/s9/resume", 202, resumed);
    const { user, fake } = setup({ versions: [versionOut()], waiting: [waitingSession()] });
    (await openReplanStream(fake)).push(acceptQuestion(councilEvents("s9")));
    await user.type(await screen.findByLabelText("Ce qu'il faut revoir"), "Pas cette semaine.");
    await user.click(screen.getByRole("button", { name: "Garder le plan actuel" }));
    await waitFor(() =>
      expect(resumes).toEqual([
        { interrupt_id: "i1", value: { action: "refuse", note: "Pas cette semaine." } },
      ]),
    );
  });

  it("keeps the end of a joined replan once it is no longer waiting (revue finale 5, C-I1)", async () => {
    recordPosts("/sessions/s9/resume", 202, resumed);
    const { user, fake, state } = setup({
      versions: [versionOut(), buildVersion()],
      waiting: [waitingSession()],
    });
    const e = councilEvents("s9");
    const socket = await openReplanStream(fake);
    socket.push(acceptQuestion(e));
    await user.click(await screen.findByRole("button", { name: "Accepter le nouveau plan" }));
    // Après la fin, le back ne rend plus de session en attente et la version est acceptée.
    state.waiting = [];
    state.versions = [versionOut({ status: "accepted" }), buildVersion()];
    socket.push(e.completed());
    expect(
      await screen.findByText("Nouveau plan accepté : ton programme est à jour."),
    ).toBeInTheDocument();
    const history = await screen.findByRole("list", { name: "Historique des versions" });
    await waitFor(() => expect(within(history).getAllByText("Acceptée")).toHaveLength(2));
    expect(
      screen.getByText("Nouveau plan accepté : ton programme est à jour."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Replanifier" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nouvelle replanification" })).toBeInTheDocument();
  });

  it("says when the current plan was kept", async () => {
    const { fake, state } = setup({ versions: [versionOut()], waiting: [waitingSession()] });
    const socket = await openReplanStream(fake);
    state.waiting = [];
    state.versions = [versionOut({ status: "refused" })];
    socket.push(councilEvents("s9").completed());
    expect(await screen.findByText("Plan actuel gardé : rien n'a changé.")).toBeInTheDocument();
  });

  it("shows a pushed deadline in the proposal (revue finale 5, C-I3)", async () => {
    setup({
      versions: [versionOut({ diff: { ...versionOut().diff, weeks_before: 8, weeks_after: 10 } })],
      waiting: [waitingSession()],
    });
    const panel = await screen.findByRole("region", { name: "Proposition du Stratège" });
    expect(within(panel).getByText("Durée du programme : 8 → 10 semaines")).toBeInTheDocument();
  });

  it("says nothing of the length when it does not change", async () => {
    setup({ versions: [versionOut()], waiting: [waitingSession()] });
    const panel = await screen.findByRole("region", { name: "Proposition du Stratège" });
    expect(within(panel).queryByText(/Durée du programme/)).not.toBeInTheDocument();
  });

  it("sends a revision note instead of accepting", async () => {
    const resumes = recordPosts("/sessions/s9/resume", 202, {
      id: "s9",
      graph: "replan",
      status: "running",
      last_seq: 0,
      pending_interrupt: null,
    });
    const { user, fake } = setup({ versions: [versionOut()], waiting: [waitingSession()] });
    (await openReplanStream(fake)).push(acceptQuestion(councilEvents("s9")));
    await user.type(
      await screen.findByLabelText("Ce qu'il faut revoir"),
      "Garde le quiz du jeudi.",
    );
    await user.click(screen.getByRole("button", { name: "Répondre" }));
    await waitFor(() =>
      expect(resumes).toEqual([
        { interrupt_id: "i1", value: { answers: { note: "Garde le quiz du jeudi." } } },
      ]),
    );
  });

  it("offers nothing to accept for a closed empty version", async () => {
    setup({
      versions: [
        versionOut({ status: "empty", diff: null, week_loads: [], reason: "Rien ne bouge." }),
        buildVersion(),
      ],
    });
    expect(await screen.findByText("Rien à changer")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Proposition du Stratège" })).toBeNull();
    expect(screen.getByRole("button", { name: "Replanifier" })).toBeInTheDocument();
  });

  it("lists version history", async () => {
    setup({
      versions: [
        versionOut({ status: "accepted", accepted_at: "2026-11-16T11:00:00Z" }),
        versionOut({ version: 3, status: "refused", review: null }),
        buildVersion(),
      ],
    });
    const history = await screen.findByRole("list", { name: "Historique des versions" });
    const items = within(history).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[0]!).getByText("Acceptée")).toBeInTheDocument();
    expect(within(items[0]!).getByText("Deux semaines de suite en retard.")).toBeInTheDocument();
    expect(within(items[1]!).getByText("Refusée")).toBeInTheDocument();
    expect(within(items[2]!).getByText("Construction du programme")).toBeInTheDocument();
    expect(
      within(items[0]!).getByText(/1 ajoutée\(s\), 1 retirée\(s\), 1 déplacée\(s\)/),
    ).toBeInTheDocument();
  });

  it("shows loading, then an empty history, then a retryable error", async () => {
    let failing = true;
    const { user } = setup({
      versionsReply: () =>
        failing
          ? HttpResponse.json(apiError("internal_error", "Panne du serveur."), { status: 500 })
          : HttpResponse.json([]),
    });
    expect(screen.getByText("Chargement de la replanification…")).toBeInTheDocument();
    expect(await screen.findByText("Panne du serveur.")).toBeInTheDocument();
    failing = false;
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Aucune version pour l'instant")).toBeInTheDocument();
  });

  it("offers a way back from an empty history (revue finale 5, C-m5)", async () => {
    const { user, router } = setup({ versions: [] });
    expect(await screen.findByText("Aucune version pour l'instant")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir le programme" }));
    expect(router.state.location.pathname).toBe("/apprendre/programme/p1");
  });
});
