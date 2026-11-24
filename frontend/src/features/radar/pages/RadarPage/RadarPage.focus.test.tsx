import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { sessionOut } from "@/test/councilApi";
import { radarRun, radarSession } from "@/test/radarApi";
import { openStream, renderRadar } from "@/test/radarHarness";
import { RadarPage } from "./RadarPage";

const setup = (api: Parameters<typeof renderRadar>[1] = {}, path?: string) =>
  renderRadar((createSocket) => <RadarPage createSocket={createSocket} />, api, path);

const RUNNING = radarRun("r9", {
  status: "running",
  finished_at: null,
  ranking: [],
  offers: [],
  blocked_domains: [],
});

describe("RadarPage focus and browser history", () => {
  it("radar focus without location state: the title takes the focus after a launch", async () => {
    const { user, state, router, sockets } = setup();
    await user.click(await screen.findByRole("button", { name: "Run a scan" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/new1"));
    // Reloading the page or going back does not restore launch state from history.
    expect(router.state.location.state).toBeNull();
    expect(await screen.findByRole("heading", { name: "Scan in progress" })).toHaveFocus();
    // The session ID from the launch response avoids a separate lookup.
    await openStream(sockets, "sess-new1");
    expect(state.sessionReads).toBe(0);
  });

  it("ignores a stale location.state: no focus taken, no note, the session is looked up", async () => {
    const { router, sockets, state } = setup({
      runs: [radarRun("r1"), RUNNING],
      sessions: [sessionOut("sess-r9", "running", radarSession("r9"))],
    });
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/r9"));
    await router.navigate("/carriere/radar/r9", {
      state: { sessionId: "sess-forged", resumed: true },
      replace: true,
    });
    const title = await screen.findByRole("heading", { name: "Scan in progress" });
    await openStream(sockets, "sess-r9");
    expect(title).not.toHaveFocus();
    expect(screen.queryByText("A scan was already in progress: following it.")).toBeNull();
    expect(sockets.sockets.some((s) => s.url.includes("sess-forged"))).toBe(false);
    expect(state.sessionReads).toBeGreaterThan(0);
  });

  it("spends the launch focus once: coming back to the running run does not take it again", async () => {
    const { user, router } = setup({ runs: [radarRun("r1")] });
    await user.click(await screen.findByRole("button", { name: "Run a scan" }));
    expect(await screen.findByRole("heading", { name: "Scan in progress" })).toHaveFocus();

    // Visit a completed scan before returning to the running scan.
    await router.navigate("/carriere/radar/r1");
    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: "Scan in progress" })).toBeNull(),
    );
    await router.navigate("/carriere/radar/new1");
    const title = await screen.findByRole("heading", { name: "Scan in progress" });
    expect(title).not.toHaveFocus();
  });
});
