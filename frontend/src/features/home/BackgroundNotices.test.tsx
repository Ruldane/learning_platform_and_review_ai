import { act, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { activityItem, type HomeApiOptions } from "@/test/homeApi";
import { renderHome } from "@/test/homeHarness";
import { BackgroundNotices } from "./BackgroundNotices";
import { useActivity } from "./hooks/useActivity";
import { useBrief } from "./hooks/useBrief";

const POLL = 40;

/** Relit le brief et le fil comme l'accueil : les notifications doivent les invalider. */
function Pages() {
  useBrief();
  useActivity();
  return null;
}

const setup = (api: HomeApiOptions = {}, dismissMs = 60_000) =>
  renderHome(
    () => (
      <>
        <Pages />
        <BackgroundNotices pollMs={POLL} dismissMs={dismissMs} />
      </>
    ),
    api,
  );

const region = () => screen.getByRole("region", { name: "Notifications" });
const T = (minute: number) => new Date(Date.UTC(2026, 10, 16, 10, minute)).toISOString();
const activityReads = (queries: URLSearchParams[]) => queries.length;

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

/** Le temps des délais de disparition est simulé : le test n'attend pas, il l'avance. */
const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));

describe("BackgroundNotices", () => {
  it("announces nothing that was already there, then what arrives, from the (at, id) cursor", async () => {
    const { state } = setup({
      events: [activityItem("e1", T(1), { title: "Vieille leçon" })],
    });
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    expect(region()).toBeEmptyDOMElement();
    const seed = state.queries.find((query) => query.get("limit") === "1");
    expect(seed?.get("after")).toBeNull();

    state.events.push(
      activityItem("e2", T(2), { title: "Leçon prête", detail: "Les jointures" }),
      activityItem("e3", T(3), { kind: "memory", title: "Souvenir" }),
    );
    expect(await within(region()).findByText("Leçon prête")).toBeVisible();
    expect(within(region()).getByText("Les jointures")).toBeVisible();
    expect(within(region()).queryByText("Souvenir")).toBeNull();
    expect(within(region()).queryByText("Vieille leçon")).toBeNull();
    const polls = state.queries.filter((query) => query.get("after"));
    expect(polls[0]?.get("after")).toBe(T(1));
    expect(polls[0]?.get("after_id")).toBe("e1");
    expect(polls[0]?.get("before")).toBeNull();
    // Le dernier vu avance : l'événement n'est pas annoncé deux fois.
    await waitFor(() => expect(state.queries.at(-1)?.get("after_id")).toBe("e3"));
    expect(within(region()).getAllByText("Leçon prête")).toHaveLength(1);
  });

  it("does not lose an event that shares its instant with the last seen one", async () => {
    const { state } = setup({ events: [activityItem("e1", T(1))] });
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    state.events.push(activityItem("e2", T(1), { kind: "radar", title: "Relevé fini" }));
    expect(await within(region()).findByText("Relevé fini")).toBeVisible();
  });

  it.each(["lesson", "radar", "brief", "project", "job_failed"])(
    "keeps the %s events",
    async (kind) => {
      const { state } = setup({ events: [activityItem("e1", T(1))] });
      await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
      state.events.push(activityItem("e2", T(2), { kind, title: `Un événement ${kind}` }));
      expect(await within(region()).findByText(`Un événement ${kind}`)).toBeVisible();
    },
  );

  it("reads the brief and the feed again when something new arrives", async () => {
    const { state } = setup({ events: [activityItem("e1", T(1))] });
    await waitFor(() => expect(state.briefReads).toBe(1));
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(2));
    const reads = state.briefReads;
    const feedReads = activityReads(state.queries);
    state.events.push(activityItem("e2", T(2), { kind: "brief", title: "Brief prêt" }));
    await within(region()).findByText("Brief prêt");
    await waitFor(() => expect(state.briefReads).toBeGreaterThan(reads));
    // Le fil est relu en plus des relectures de fond : une lecture sans `after` en témoigne.
    await waitFor(() =>
      expect(state.queries.slice(feedReads).some((query) => query.get("after") === null)).toBe(
        true,
      ),
    );
  });

  it("reads nothing while the tab is hidden, and goes on when it is visible again", async () => {
    const { state } = setup({ events: [activityItem("e1", T(1))] });
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    await new Promise((resolve) => setTimeout(resolve, POLL * 2));
    const frozen = state.queries.length;
    state.events.push(activityItem("e2", T(2), { title: "Pendant l'absence" }));
    await new Promise((resolve) => setTimeout(resolve, POLL * 6));
    expect(state.queries.length).toBe(frozen);
    expect(within(region()).queryByText("Pendant l'absence")).toBeNull();

    vi.restoreAllMocks();
    expect(await within(region()).findByText("Pendant l'absence")).toBeVisible();
  });

  it("closes one notice and keeps the others", async () => {
    const { state, user } = setup({ events: [activityItem("e1", T(1))] });
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    state.events.push(
      activityItem("e2", T(2), { title: "Première" }),
      activityItem("e3", T(3), { title: "Seconde" }),
    );
    expect(await within(region()).findByText("Seconde")).toBeVisible();
    await user.click(
      within(region()).getByRole("button", { name: "Close notification: Seconde" }),
    );
    expect(within(region()).queryByText("Seconde")).toBeNull();
    expect(within(region()).getByText("Première")).toBeVisible();
  });

  it("catch-up notices capped at three: a burst keeps the three latest, the latest first", async () => {
    const { state } = setup({ events: [activityItem("e1", T(1))] });
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    state.events.push(
      ...[2, 3, 4, 5, 6].map((n) => activityItem(`e${n}`, T(n), { title: `Nouveauté ${n}` })),
    );
    await within(region()).findByText("Nouveauté 6");
    const titles = within(region())
      .getAllByRole("button", { name: /Close notification/ })
      .map((button) => button.getAttribute("aria-label"));
    expect(titles).toEqual([
      "Close notification: Nouveauté 6",
      "Close notification: Nouveauté 5",
      "Close notification: Nouveauté 4",
    ]);
    // Les plus anciennes de la rafale ne sont ni montrées plus tard, ni annoncées une seconde fois.
    await new Promise((resolve) => setTimeout(resolve, POLL * 5));
    expect(within(region()).queryByText("Nouveauté 2")).toBeNull();
    expect(within(region()).queryByText("Nouveauté 3")).toBeNull();
  });

  it("keeps the notices of an earlier read in front of the next ones", async () => {
    const { state } = setup({ events: [activityItem("e1", T(1))] });
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    state.events.push(activityItem("e2", T(2), { title: "Première" }));
    await within(region()).findByText("Première");
    state.events.push(activityItem("e3", T(3), { title: "Seconde" }));
    await within(region()).findByText("Seconde");
    const titles = within(region())
      .getAllByRole("button", { name: /Close notification/ })
      .map((button) => button.getAttribute("aria-label"));
    expect(titles).toEqual([
      "Close notification: Première",
      "Close notification: Seconde",
    ]);
  });

  it(
    "notice pauses on hover and focus, then goes on with the time it had left",
    { timeout: 20_000 },
    async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      const { state, user } = setup({ events: [activityItem("e1", T(1))] }, 2_000);
      await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
      state.events.push(
        activityItem("e2", T(2), { title: "Survolée" }),
        activityItem("e3", T(3), { title: "Laissée" }),
      );
      const hovered = (await within(region()).findByText("Survolée")).closest("[data-notice]")!;
      await user.hover(hovered);
      // « Laissée » disparaît à ses 2 s, « Survolée » attend qu'on la quitte, quelle que soit la
      // durée.
      await advance(2_200);
      expect(within(region()).queryByText("Laissée")).toBeNull();
      await advance(8_000);
      expect(within(region()).getByText("Survolée")).toBeVisible();
      await user.unhover(hovered);
      await advance(2_200);
      expect(within(region()).queryByText("Survolée")).toBeNull();
    },
  );

  it("holds a notice while its close button has focus", { timeout: 20_000 }, async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { state, user } = setup({ events: [activityItem("e1", T(1))] }, 2_000);
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    state.events.push(activityItem("e2", T(2), { title: "Au clavier" }));
    await within(region()).findByText("Au clavier");
    await user.tab();
    expect(within(region()).getByRole("button", { name: /Close notification/ })).toHaveFocus();
    await advance(8_000);
    expect(within(region()).getByText("Au clavier")).toBeVisible();
    await user.tab();
    await advance(2_200);
    expect(within(region()).queryByText("Au clavier")).toBeNull();
  });
});
