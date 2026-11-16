import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useCaptureRequest } from "@/shared/lib/captureRequest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { councilEvents } from "@/test/councilEvents";
import { activityItem, type HomeApiOptions } from "@/test/homeApi";
import { openStream, renderHome } from "@/test/homeHarness";
import { HomePage } from "./HomePage";

const setup = (api: HomeApiOptions = {}) =>
  renderHome((createSocket) => <HomePage createSocket={createSocket} />, api);

/** `n` événements, du plus récent (`e01`) au plus ancien, une minute d'écart. */
const events = (n: number) =>
  Array.from({ length: n }, (_, index) =>
    activityItem(
      `e${String(index + 1).padStart(2, "0")}`,
      new Date(Date.UTC(2026, 10, 16, 10, 59 - index)).toISOString(),
    ),
  );

const feed = () => screen.findByRole("list", { name: "Activité récente" });

describe("HomePage", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("s9");
    useCaptureRequest.setState({ count: 0 });
  });

  it("shows the brief with its seven sections, in the order of F17", async () => {
    setup({ events: events(2) });
    expect(await screen.findByText(/lundi 16 novembre/)).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Ton brief du jour" })).toBeVisible();
    await feed();
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual([
      "Ton bloc du jour",
      "Révisions",
      "Relances",
      "Nouvelles offres",
      "Ta semaine",
      "Une ressource pour toi",
      "Le conseil",
      "Activité récente",
    ]);
    expect(screen.getByText("Leçon : Les jointures SQL")).toBeVisible();
    expect(screen.getByText("12 fiches à réviser aujourd'hui.")).toBeVisible();
    expect(screen.getByText("Société Fictive, poste Data engineer")).toBeVisible();
    expect(screen.getByText("score 78 sur 100")).toBeVisible();
    expect(screen.getByText("3 h 10 sur 5 h prévues")).toBeVisible();
    expect(screen.getByText("Comprendre les index")).toBeVisible();
    expect(screen.getByText("Garde ta série en révisant tes fiches ce soir.")).toBeVisible();
  });

  it("sends the quick actions to their screens", async () => {
    const { user, router } = setup();
    for (const [name, path] of [
      ["Commencer mon bloc", "/etudier/session"],
      ["Réviser", "/etudier/revisions"],
      ["Ajouter une offre", "/carriere/offres"],
    ] as const) {
      const group = await screen.findByRole("group", { name: "Actions rapides" });
      await user.click(within(group).getByRole("button", { name }));
      await waitFor(() => expect(router.state.location.pathname).toBe(path));
      await router.navigate("/");
    }
  });

  it("opens a follow-up from the brief and the capture from the quick actions", async () => {
    const { user, router } = setup();
    await user.click(
      await screen.findByRole("button", { name: "Société Fictive, poste Data engineer" }),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
    await router.navigate("/");
    const group = await screen.findByRole("group", { name: "Actions rapides" });
    expect(useCaptureRequest.getState().count).toBe(0);
    await user.click(within(group).getByRole("button", { name: "Capturer" }));
    expect(useCaptureRequest.getState().count).toBe(1);
    expect(router.state.location.pathname).toBe("/");
  });

  it("offers to start with a goal when there is no program", async () => {
    const { user, router } = setup({ brief: { week: null, block: null } });
    expect(await screen.findByRole("heading", { name: "Pas encore de programme" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Ta semaine" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Révisions" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Commence par un objectif" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/apprendre/objectifs"));
  });

  it("pages the activity feed by the (at, id) pair, without losing or repeating a tie", async () => {
    const rows = events(25);
    // Les événements 20 et 21 partagent un instant : la page s'arrête au milieu de l'égalité.
    rows[20] = { ...rows[20]!, at: rows[19]!.at };
    const { user, state } = setup({ events: rows });
    const queries = state.queries;
    expect(await within(await feed()).findAllByRole("listitem")).toHaveLength(20);
    expect(queries.at(-1)?.get("before")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Voir plus" }));
    await waitFor(() =>
      expect(
        within(screen.getByRole("list", { name: "Activité récente" })).getAllByRole("listitem"),
      ).toHaveLength(25),
    );
    const older = queries.at(-1)!;
    const last = [...rows].sort(
      (a, b) => Date.parse(b.at) - Date.parse(a.at) || (a.id < b.id ? 1 : -1),
    )[19]!;
    expect(older.get("before")).toBe(last.at);
    expect(older.get("before_id")).toBe(last.id);
    const titles = within(screen.getByRole("list", { name: "Activité récente" }))
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    expect(new Set(titles).size).toBe(25);
    expect(screen.queryByRole("button", { name: "Voir plus" })).toBeNull();
  });

  it("keeps the brief when the feed cannot be read", async () => {
    setup({ activityFails: true });
    expect(await screen.findByText("Le fil n'a pas pu être lu.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Ton bloc du jour" })).toBeVisible();
  });

  it("follows a pending advice and reads the brief again when the session ends", async () => {
    const { sockets, state } = setup({
      brief: { advice_status: "pending", advice: null, session_id: "s9" },
    });
    expect(await screen.findByText("Le conseil se réunit…")).toBeVisible();
    const stream = await openStream(sockets, "s9");
    const reads = state.briefReads;
    state.brief = {
      ...state.brief,
      advice_status: "ready",
      advice: ["Phrase du conseil un.", "Phrase du conseil deux."],
      session_id: null,
    };
    stream.push(councilEvents("s9").completed());
    expect(await screen.findByText("Phrase du conseil un.")).toBeVisible();
    expect(screen.queryByText("Le conseil se réunit…")).toBeNull();
    expect(state.briefReads).toBe(reads + 1);
  });

  it.each(["failed", "unavailable"])(
    "says the advice has nothing to say today (%s), with no retry and no key wording",
    async (status) => {
      const { state } = setup({ brief: { advice_status: status, advice: null, session_id: null } });
      expect(await screen.findByText("Le conseil n'a rien pu dire ce matin.")).toBeVisible();
      expect(screen.queryByRole("button", { name: "Réessayer" })).toBeNull();
      expect(screen.queryByText(/clé/i)).toBeNull();
      expect(state.briefReads).toBe(1);
    },
  );

  it("shows the loading state, then an error with a retry that reads the brief again", async () => {
    const { user } = setup({ briefFailures: 1 });
    expect(screen.getByRole("status")).toHaveTextContent("Ton brief se prépare…");
    expect(await screen.findByRole("alert")).toHaveTextContent("Le brief n'a pas pu être lu.");
    expect(screen.getByRole("heading", { level: 1, name: "Ton brief du jour" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Ton bloc du jour" })).toBeVisible();
  });
});
