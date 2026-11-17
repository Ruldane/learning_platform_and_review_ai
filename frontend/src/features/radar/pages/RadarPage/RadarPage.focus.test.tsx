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

describe("RadarPage : le focus ne dépend pas de l'historique du navigateur", () => {
  it("radar focus without location state: the title takes the focus after a launch", async () => {
    const { user, state, router, sockets } = setup();
    await user.click(await screen.findByRole("button", { name: "Lancer un relevé" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/carriere/radar/new1"));
    // Rien n'est écrit dans l'historique : un rechargement ou un retour arrière n'en relirait rien.
    expect(router.state.location.state).toBeNull();
    expect(await screen.findByRole("heading", { name: "Relevé en cours" })).toHaveFocus();
    // La session du 202 est suivie sans la chercher par son sujet.
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
    const title = await screen.findByRole("heading", { name: "Relevé en cours" });
    await openStream(sockets, "sess-r9");
    expect(title).not.toHaveFocus();
    expect(screen.queryByText("Un relevé était déjà en cours : on le suit.")).toBeNull();
    expect(sockets.sockets.some((s) => s.url.includes("sess-forged"))).toBe(false);
    expect(state.sessionReads).toBeGreaterThan(0);
  });

  it("spends the launch focus once: coming back to the running run does not take it again", async () => {
    const { user, router } = setup({ runs: [radarRun("r1")] });
    await user.click(await screen.findByRole("button", { name: "Lancer un relevé" }));
    expect(await screen.findByRole("heading", { name: "Relevé en cours" })).toHaveFocus();

    // Un détour par un relevé fini de l'historique, puis retour sur le relevé encore en cours.
    await router.navigate("/carriere/radar/r1");
    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: "Relevé en cours" })).toBeNull(),
    );
    await router.navigate("/carriere/radar/new1");
    const title = await screen.findByRole("heading", { name: "Relevé en cours" });
    expect(title).not.toHaveFocus();
  });
});
