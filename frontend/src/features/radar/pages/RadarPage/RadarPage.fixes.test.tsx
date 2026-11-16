import { act, screen, waitFor, within } from "@testing-library/react";
import { HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { apiError } from "@/test/councilHarness";
import { radarRun, radarSession } from "@/test/radarApi";
import { openStream, renderRadar } from "@/test/radarHarness";
import { RadarPage } from "./RadarPage";

const setup = (api: Parameters<typeof renderRadar>[1] = {}, path?: string) =>
  renderRadar((createSocket) => <RadarPage createSocket={createSocket} />, api, path);

const running = (id: string) =>
  radarRun(id, {
    status: "running",
    finished_at: null,
    ranking: [],
    offers: [],
    blocked_domains: [],
  });

describe("RadarPage : un seul lancement, une seule session", () => {
  it("sends one launch on a double click and follows the session of the 202", async () => {
    const { user, state, sockets } = setup();
    await user.dblClick(await screen.findByRole("button", { name: "Lancer un relevé" }));
    await openStream(sockets, "sess-new1");
    expect(state.bodies).toHaveLength(1);
    expect(state.runs.filter((run) => run.status === "running")).toHaveLength(1);
    expect(screen.queryByText("Un relevé était déjà en cours : on le suit.")).toBeNull();
    expect(sockets.sockets.map((s) => s.url).filter((url) => url.includes("/stream"))).toHaveLength(
      1,
    );
  });

  it("picks the session whose subject is the run among several radar sessions", async () => {
    const { sockets } = setup({
      runs: [running("r9"), radarRun("r1")],
      sessions: [
        sessionOut("sess-other", "running", radarSession("r5")),
        // Même sujet, autre parcours : à écarter.
        sessionOut("sess-wrong-graph", "running", {
          graph: "learning_council",
          subject_type: "goal",
          subject_id: "r9",
        }),
        sessionOut("sess-r9", "running", radarSession("r9")),
        sessionOut("sess-old", "completed", radarSession("r1")),
      ],
    });
    await openStream(sockets, "sess-r9");
    const streams = sockets.sockets.filter((s) => s.url.includes("/stream"));
    expect(streams).toHaveLength(1);
  });
});

describe("RadarPage : relevé fini sans que le flux le dise", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("re-enables the form and refreshes the history when the fallback read sees the end", async () => {
    const { state, finish, sockets } = setup({
      runs: [running("r9")],
      sessions: [sessionOut("sess-r9", "running", radarSession("r9"))],
    });
    await openStream(sockets, "sess-r9");
    expect(await screen.findByRole("button", { name: "Relevé en cours…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(
      within(screen.getByRole("list", { name: "Relevés précédents" })).getByText("En cours"),
    ).toBeVisible();

    // Le flux reste muet : seul le repli de 10 s peut voir la fin.
    finish("r9");
    await act(() => vi.advanceTimersByTimeAsync(10_500));
    expect(await screen.findByRole("button", { name: "Lancer un relevé" })).toHaveAttribute(
      "aria-disabled",
      "false",
    );
    const history = screen.getByRole("list", { name: "Relevés précédents" });
    expect(within(history).getByText("Terminé")).toBeVisible();
    expect(within(history).queryByText("En cours")).toBeNull();
    expect(state.latestReads).toBeGreaterThan(1);
  });
});

describe("RadarPage : messages et redirections", () => {
  it("clears a server refusal on a field as soon as that field is edited", async () => {
    const { user } = setup({
      startReply: () =>
        HttpResponse.json(apiError("validation_error", "Requête invalide.", { fields: ["zone"] }), {
          status: 422,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Lancer un relevé" }));
    const zone = await screen.findByLabelText("Zone");
    await waitFor(() => expect(zone).toBeInvalid());
    await user.type(zone, "x");
    expect(zone).toBeValid();
    expect(zone).not.toHaveAccessibleDescription(/pas acceptée/);
  });

  it("drops the « already running » note once the run is over", async () => {
    const { user, state, finish, sockets } = setup({ runs: [radarRun("r1")] });
    await screen.findByText("47 offres lues · 6 bloquées · 41 analysées");
    state.runs.unshift(running("r9"));
    state.sessions.push(sessionOut("sess-r9", "running", radarSession("r9")));
    await user.click(screen.getByRole("button", { name: "Lancer un relevé" }));
    expect(await screen.findByText("Un relevé était déjà en cours : on le suit.")).toBeVisible();

    const stream = await openStream(sockets, "sess-r9");
    finish("r9");
    stream.push(councilEvents("sess-r9").completed());
    await screen.findByRole("heading", { name: "Compétences les plus demandées" });
    expect(screen.queryByText("Un relevé était déjà en cours : on le suit.")).toBeNull();
  });

  it("follows a scheduled run that starts after the page's own run is over", async () => {
    const { user, state, finish, sockets, router } = setup();
    await user.click(await screen.findByRole("button", { name: "Lancer un relevé" }));
    const stream = await openStream(sockets, "sess-new1");
    // Le relevé du lundi démarre à la fin du premier.
    finish("new1");
    state.runs.unshift(running("r9"));
    state.sessions.push(sessionOut("sess-r9", "running", radarSession("r9")));
    stream.push(councilEvents("sess-new1").completed());
    await screen.findByRole("heading", { name: "Compétences les plus demandées" });

    await act(() => router.navigate("/carriere/radar"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/r9"));
  });
});
