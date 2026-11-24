import { screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useCaptureRequest } from "@/shared/lib/captureRequest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { councilEvents } from "@/test/councilEvents";
import { activityItem, type HomeApiOptions } from "@/test/homeApi";
import { openStream, renderHome } from "@/test/homeHarness";
import { BackgroundNotices } from "../../BackgroundNotices";
import { HomePage } from "./HomePage";

const setup = (api: HomeApiOptions = {}, rereadMs?: number) =>
  renderHome((createSocket) => <HomePage createSocket={createSocket} rereadMs={rereadMs} />, api);

/** `n` événements, du plus récent (`e01`) au plus ancien, une minute d'écart. */
const events = (n: number) =>
  Array.from({ length: n }, (_, index) =>
    activityItem(
      `e${String(index + 1).padStart(2, "0")}`,
      new Date(Date.UTC(2026, 10, 16, 10, 59 - index)).toISOString(),
    ),
  );

const feed = () => screen.findByRole("list", { name: "Recent activity" });

describe("HomePage", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("s9");
    useCaptureRequest.setState({ count: 0 });
  });

  it("shows the brief with its seven sections, in the order of F17", async () => {
    setup({ events: events(2) });
    expect(await screen.findByText(/Monday 16 November/)).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "Your daily brief" })).toBeVisible();
    await feed();
    const headings = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual([
      "Your daily block",
      "Reviews",
      "Follow-ups",
      "New postings",
      "Your week",
      "A resource for you",
      "The council",
      "Recent activity",
    ]);
    expect(screen.getByText("Lesson: Les jointures SQL")).toBeVisible();
    expect(screen.getByText("12 cards to review today.")).toBeVisible();
    expect(screen.getByText("Société Fictive, Data engineer role")).toBeVisible();
    expect(screen.getByText("score 78 out of 100")).toBeVisible();
    expect(screen.getByText("3 h 10 of 5 h planned")).toBeVisible();
    expect(screen.getByText("Comprendre les index")).toBeVisible();
    expect(screen.getByText("Garde ta série en révisant tes fiches ce soir.")).toBeVisible();
  });

  it("sends the quick actions to their screens", async () => {
    const { user, router } = setup();
    for (const [name, path] of [
      ["Start my block", "/study/session"],
      ["Review", "/study/reviews"],
      ["Add a posting", "/career/postings"],
    ] as const) {
      const group = await screen.findByRole("group", { name: "Quick actions" });
      await user.click(within(group).getByRole("button", { name }));
      await waitFor(() => expect(router.state.location.pathname).toBe(path));
      await router.navigate("/");
    }
  });

  it("opens a follow-up from the brief and the capture from the quick actions", async () => {
    const { user, router } = setup();
    await user.click(
      await screen.findByRole("button", { name: "Société Fictive, Data engineer role" }),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe("/applications/a1"));
    await router.navigate("/");
    const group = await screen.findByRole("group", { name: "Quick actions" });
    expect(useCaptureRequest.getState().count).toBe(0);
    await user.click(within(group).getByRole("button", { name: "Capture" }));
    expect(useCaptureRequest.getState().count).toBe(1);
    expect(router.state.location.pathname).toBe("/");
  });

  it("offers to start with a goal when there is no program", async () => {
    const { user, router } = setup({ brief: { week: null, block: null } });
    expect(await screen.findByRole("heading", { name: "No program yet" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Your week" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Reviews" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Start with a goal" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/learn/goals"));
  });

  it("pages the activity feed by the (at, id) pair, without losing or repeating a tie", async () => {
    const rows = events(25);
    // Les événements 20 et 21 partagent un instant : la page s'arrête au milieu de l'égalité.
    rows[20] = { ...rows[20]!, at: rows[19]!.at };
    const { user, state } = setup({ events: rows });
    const queries = state.queries;
    expect(await within(await feed()).findAllByRole("listitem")).toHaveLength(20);
    expect(queries.at(-1)?.get("before")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Show more" }));
    await waitFor(() =>
      expect(
        within(screen.getByRole("list", { name: "Recent activity" })).getAllByRole("listitem"),
      ).toHaveLength(25),
    );
    const older = queries.at(-1)!;
    const last = [...rows].sort(
      (a, b) => Date.parse(b.at) - Date.parse(a.at) || (a.id < b.id ? 1 : -1),
    )[19]!;
    expect(older.get("before")).toBe(last.at);
    expect(older.get("before_id")).toBe(last.id);
    const titles = within(screen.getByRole("list", { name: "Recent activity" }))
      .getAllByRole("listitem")
      .map((item) => item.textContent);
    expect(new Set(titles).size).toBe(25);
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
  });

  it("keeps the brief when the feed cannot be read", async () => {
    setup({ activityFails: true });
    expect(await screen.findByText("Le fil n'a pas pu être lu.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Your daily block" })).toBeVisible();
  });

  it("follows a pending advice and reads the brief again when the session ends", async () => {
    const { sockets, state } = setup({
      brief: { advice_status: "pending", advice: null, session_id: "s9" },
    });
    expect(await screen.findByText("The council is meeting…")).toBeVisible();
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
    expect(screen.queryByText("The council is meeting…")).toBeNull();
    expect(state.briefReads).toBe(reads + 1);
  });

  it("reads a brief that is still pending once more, then stops", async () => {
    const { sockets, state } = setup(
      { brief: { advice_status: "pending", advice: null, session_id: "s9" } },
      40,
    );
    expect(await screen.findByText("The council is meeting…")).toBeVisible();
    const stream = await openStream(sockets, "s9");
    const reads = state.briefReads;
    stream.push(councilEvents("s9").completed());
    await waitFor(() => expect(state.briefReads).toBe(reads + 2));
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(state.briefReads).toBe(reads + 2);
    expect(screen.getByText("The council is meeting…")).toBeVisible();
  });

  it("keeps the feed continuous when a new event arrives after loading more", async () => {
    const { user, state } = renderHome(
      (createSocket) => (
        <>
          <HomePage createSocket={createSocket} />
          <BackgroundNotices pollMs={40} />
        </>
      ),
      { events: events(40) },
    );
    await user.click(await screen.findByRole("button", { name: "Show more" }));
    const ids = () =>
      within(screen.getByRole("list", { name: "Recent activity" }))
        .getAllByRole("listitem")
        .map((item) => /Événement (e\d\d|n1)/.exec(item.textContent ?? "")?.[1]);
    await waitFor(() => expect(ids()).toHaveLength(40));
    const expected = Array.from({ length: 40 }, (_, i) => `e${String(i + 1).padStart(2, "0")}`);
    expect(ids()).toEqual(expected);
    state.events.push(
      activityItem("n1", new Date(Date.UTC(2026, 10, 16, 11, 30)).toISOString(), {
        kind: "memory",
      }),
    );
    await waitFor(() => expect(ids()).toHaveLength(41));
    expect(ids()).toEqual(["n1", ...expected]);
  });

  it.each(["failed", "unavailable"])(
    "says the advice has nothing to say today (%s), with no retry and no key wording",
    async (status) => {
      const { state } = setup({ brief: { advice_status: status, advice: null, session_id: null } });
      expect(
        await screen.findByText("The council had nothing to say this morning."),
      ).toBeVisible();
      expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
      expect(screen.queryByText(/\bkey\b/i)).toBeNull();
      expect(state.briefReads).toBe(1);
    },
  );

  it("shows the loading state, then an error with a retry that reads the brief again", async () => {
    const { user } = setup({ briefFailures: 1 });
    expect(screen.getByRole("status")).toHaveTextContent("Preparing your brief…");
    expect(await screen.findByRole("alert")).toHaveTextContent("Le brief n'a pas pu être lu.");
    expect(screen.getByRole("heading", { level: 1, name: "Your daily brief" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: "Your daily block" })).toBeVisible();
  });

  it("names the rubrics whose source failed instead of showing a false zero", async () => {
    setup({
      brief: {
        reminders: { due: 0, items: [] },
        reviews: { queue: 0, remaining: 0 },
        week: null,
        unavailable: ["reminders", "reviews", "week"],
      },
      events: [],
    });
    expect(await screen.findByRole("heading", { name: "Follow-ups" })).toBeVisible();
    expect(screen.getAllByText("Section unavailable this morning.")).toHaveLength(3);
    expect(screen.queryByText("No follow-ups due.")).toBeNull();
    expect(screen.queryByText("No reviews due today.")).toBeNull();
    // Une semaine indisponible n'est pas « aucun programme » : le bloc reste montré.
    expect(screen.queryByText("No program yet")).toBeNull();
    expect(screen.getByRole("heading", { name: "Your daily block" })).toBeVisible();
  });
});
