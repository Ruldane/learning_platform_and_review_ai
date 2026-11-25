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

describe("RadarPage launch and session", () => {
  it("sends one launch on a double click and follows the session of the 202", async () => {
    const { user, state, sockets } = setup();
    await user.dblClick(await screen.findByRole("button", { name: "Run a scan" }));
    await openStream(sockets, "sess-new1");
    expect(state.bodies).toHaveLength(1);
    expect(state.runs.filter((run) => run.status === "running")).toHaveLength(1);
    expect(screen.queryByText("A scan was already in progress: following it.")).toBeNull();
    expect(sockets.sockets.map((s) => s.url).filter((url) => url.includes("/stream"))).toHaveLength(
      1,
    );
  });

  it("picks the session whose subject is the run among several radar sessions", async () => {
    const { sockets } = setup({
      runs: [running("r9"), radarRun("r1")],
      sessions: [
        sessionOut("sess-other", "running", radarSession("r5")),
        // This session has the same subject ID but belongs to a different workflow.
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

describe("RadarPage polling after a silent stream", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("re-enables the form and refreshes the history when the fallback read sees the end", async () => {
    const { state, finish, sockets } = setup({
      runs: [running("r9")],
      sessions: [sessionOut("sess-r9", "running", radarSession("r9"))],
    });
    await openStream(sockets, "sess-r9");
    expect(await screen.findByRole("button", { name: "Scan in progress…" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(
      within(screen.getByRole("list", { name: "Previous scans" })).getByText("Running"),
    ).toBeVisible();

    // The poll sees completion even when the stream sends no update.
    finish("r9");
    await act(() => vi.advanceTimersByTimeAsync(10_500));
    expect(await screen.findByRole("button", { name: "Run a scan" })).toHaveAttribute(
      "aria-disabled",
      "false",
    );
    const history = screen.getByRole("list", { name: "Previous scans" });
    expect(within(history).getByText("Done")).toBeVisible();
    expect(within(history).queryByText("Running")).toBeNull();
    expect(state.latestReads).toBeGreaterThan(1);
  });
});

describe("RadarPage messages and redirects", () => {
  it("clears a server refusal on a field as soon as that field is edited", async () => {
    const { user } = setup({
      startReply: () =>
        HttpResponse.json(apiError("validation_error", "Invalid request.", { fields: ["zone"] }), {
          status: 422,
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Run a scan" }));
    const zone = await screen.findByLabelText("Area");
    await waitFor(() => expect(zone).toBeInvalid());
    await user.type(zone, "x");
    expect(zone).toBeValid();
    expect(zone).not.toHaveAccessibleDescription(/This area isn’t accepted/);
  });

  it("clears the already running notice once the scan is over", async () => {
    const { user, state, finish, sockets } = setup({ runs: [radarRun("r1")] });
    await screen.findByText("47 postings read · 6 blocked · 41 analyzed");
    state.runs.unshift(running("r9"));
    state.sessions.push(sessionOut("sess-r9", "running", radarSession("r9")));
    await user.click(screen.getByRole("button", { name: "Run a scan" }));
    expect(await screen.findByText("A scan was already in progress: following it.")).toBeVisible();

    const stream = await openStream(sockets, "sess-r9");
    finish("r9");
    stream.push(councilEvents("sess-r9").completed());
    await screen.findByRole("heading", { name: "Most in-demand skills" });
    expect(screen.queryByText("A scan was already in progress: following it.")).toBeNull();
  });

  it("follows a scheduled run that starts after the page's own run is over", async () => {
    const { user, state, finish, sockets, router } = setup();
    await user.click(await screen.findByRole("button", { name: "Run a scan" }));
    const stream = await openStream(sockets, "sess-new1");
    // The scheduled scan starts as the first scan ends.
    finish("new1");
    state.runs.unshift(running("r9"));
    state.sessions.push(sessionOut("sess-r9", "running", radarSession("r9")));
    stream.push(councilEvents("sess-new1").completed());
    await screen.findByRole("heading", { name: "Most in-demand skills" });

    await act(() => router.navigate("/career/radar"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/career/radar/r9"));
  });
});
