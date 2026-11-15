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

const KIT_ROUTE = "candidatures/:applicationId/kit";

function setup(options: KitApiOptions = {}, api: Parameters<typeof renderApplications>[2] = {}) {
  const sockets = createFakeSocketServer();
  const kit = kitApi(options);
  server.use(...kit.handlers);
  const routes = applicationsManifest.routes.map((route) =>
    route.path === KIT_ROUTE
      ? { path: route.path, element: <KitPage createSocket={sockets.factory} /> }
      : route,
  );
  const view = renderApplications(routes, "/candidatures/a1/kit", {
    applications: [applicationOut({ id: "a1", company: "Acme", title: "Data engineer" })],
    ...api,
  });
  return { ...view, sockets, kit };
}

describe("KitPage, relance", () => {
  beforeEach(() => useSessionStore.getState().reset("k1"));

  it("says the pieces January edited are kept when she relaunches the kit", async () => {
    const { user, kit, sockets } = setup({
      items: [kitItem("letter", { edited: true }), kitItem("cv")],
    });
    expect(await screen.findByText("Modifiée par toi")).toBeVisible();
    expect(
      screen.getByText(/Les pièces que tu as modifiées sont gardées telles quelles/),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Relancer le kit" }));
    await waitFor(() => expect(kit.state.starts).toBe(1));
    await openStream(sockets, "k1");
  });

  it("does not say every piece arrived when a relaunch has only just started", async () => {
    const { user, kit, sockets } = setup({
      items: [kitItem("cv"), kitItem("letter"), kitItem("pitch", { edited: true })],
    });
    await user.click(await screen.findByRole("button", { name: "Relancer le kit" }));
    const stream = await openStream(sockets, "k1");
    // Seule la pièce modifiée par January est déjà « arrivée » : elle est gardée telle quelle.
    expect(await screen.findByText("1 pièce sur 7 est arrivée.")).toBeVisible();
    kit.arrive("letter", { content: "Refaite.", updated_at: "2026-11-15T12:00:00Z" });
    stream.push(councilEvents("k1").artifactReady("kit_item", "k-letter", null));
    expect(await screen.findByText("2 pièces sur 7 sont arrivées.")).toBeVisible();
  });
});
