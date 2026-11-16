import { screen, waitFor, within } from "@testing-library/react";
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

afterEach(() => vi.restoreAllMocks());

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

  it("closes a notice by itself after its delay, and on Fermer", async () => {
    const { state, user } = setup({ events: [activityItem("e1", T(1))] }, 250);
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    state.events.push(
      activityItem("e2", T(2), { title: "Première" }),
      activityItem("e3", T(3), { title: "Seconde" }),
    );
    expect(await within(region()).findByText("Seconde")).toBeVisible();
    await user.click(
      within(region()).getByRole("button", { name: /Fermer la notification : Seconde/ }),
    );
    expect(within(region()).queryByText("Seconde")).toBeNull();
    expect(within(region()).getByText("Première")).toBeVisible();
    await waitFor(() => expect(within(region()).queryByText("Première")).toBeNull());
  });

  it("shows three notices at most and the next ones as the first ones go", async () => {
    const { state } = setup({ events: [activityItem("e1", T(1))] }, 300);
    await waitFor(() => expect(state.queries.length).toBeGreaterThan(1));
    state.events.push(
      ...[2, 3, 4, 5, 6].map((n) => activityItem(`e${n}`, T(n), { title: `Nouveauté ${n}` })),
    );
    await within(region()).findByText("Nouveauté 2");
    expect(within(region()).getAllByRole("button", { name: /Fermer/ })).toHaveLength(3);
    expect(within(region()).queryByText("Nouveauté 6")).toBeNull();
    expect(await within(region()).findByText("Nouveauté 6")).toBeVisible();
  });
});
