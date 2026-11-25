import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { kitApi, kitItem, type KitApiOptions } from "@/test/kitApi";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { KitPage } from "./KitPage";

const KIT_ROUTE = "applications/:applicationId/kit";

function setup(options: KitApiOptions = {}, api: Parameters<typeof renderApplications>[2] = {}) {
  const sockets = createFakeSocketServer();
  const kit = kitApi(options);
  server.use(...kit.handlers);
  const routes = applicationsManifest.routes.map((route) =>
    route.path === KIT_ROUTE
      ? { path: route.path, element: <KitPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/applications/a1/kit", {
    applications: [applicationOut({ id: "a1", company: "Acme", title: "Data engineer" })],
    ...api,
  });
  return { ...view, sockets, kit };
}

describe("KitPage, regenerating a kit", () => {
  beforeEach(() => useSessionStore.getState().reset("k1"));

  it("says the pieces January edited are kept when she relaunches the kit", async () => {
    const { user, kit, sockets } = setup({
      items: [kitItem("letter", { edited: true }), kitItem("cv")],
    });
    expect(await screen.findByText("Edited by you")).toBeVisible();
    expect(
      screen.getByText(/Pieces you edited are kept as they are/),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Regenerate the kit" }));
    await waitFor(() => expect(kit.state.starts).toBe(1));
    await openStream(sockets, "k1");
  });

  it("does not say every piece arrived when a relaunch has only just started", async () => {
    const { user, kit, sockets } = setup({
      items: [kitItem("cv"), kitItem("letter"), kitItem("pitch", { edited: true })],
    });
    await user.click(await screen.findByRole("button", { name: "Regenerate the kit" }));
    const stream = await openStream(sockets, "k1");
    // The edited piece carries over and is already counted when the run starts.
    expect(await screen.findByText("1 of 7 pieces has arrived.")).toBeVisible();
    kit.arrive("letter", { content: "Refaite.", updated_at: "2026-11-15T12:00:00Z" });
    stream.push(councilEvents("k1").artifactReady("kit_item", "k-letter", null));
    expect(await screen.findByText("2 of 7 pieces have arrived.")).toBeVisible();
  });
});
