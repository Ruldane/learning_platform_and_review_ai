import { screen } from "@testing-library/react";
import { HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut } from "@/test/applicationsApi";
import { openStream, renderApplications } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { apiError } from "@/test/councilHarness";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { kitApi, kitItem, type KitApiOptions } from "@/test/kitApi";
import { server } from "@/test/server";
import { applicationsManifest } from "../../manifest";
import { KitPage } from "./KitPage";

const KIT_ROUTE = "applications/:applicationId/kit";

function setup(options: KitApiOptions = {}) {
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
  });
  return { ...view, sockets, kit };
}

const piece = (title: string) => screen.findByRole("region", { name: title });

describe("KitPage, suivre un kit déjà ouvert", () => {
  beforeEach(() => useSessionStore.getState().reset("k1"));

  it("follows a kit that is already running when the page opens, without starting another", async () => {
    const { sockets, kit } = setup({
      running: true,
      sessionId: "k9",
      items: [kitItem("cv")],
    });
    await openStream(sockets, "k9");
    expect(kit.state.starts).toBe(0);
    expect(await screen.findByText(/Le kit se prépare/)).toBeVisible();
    expect((await piece("CV ciblé")).textContent).toContain("Prête");
    expect((await piece("Lettre de motivation")).textContent).toContain("En préparation");
  });

  /** Le kit s'ouvre ailleurs (session `k7`) entre la lecture et le clic : le serveur dit 409, puis rend « en cours ». */
  function openedElsewhere() {
    const box: { kit?: ReturnType<typeof setup>["kit"] } = {};
    const start = () => {
      if (box.kit) {
        box.kit.state.running = true;
        box.kit.state.sessionId = "k7";
      }
      return HttpResponse.json(
        apiError("kit_in_progress", "Un kit est déjà en cours.", { session_id: "k7" }),
        { status: 409 },
      );
    };
    const view = setup({ start });
    box.kit = view.kit;
    return view;
  }

  it("drops the « tu le suis ici » note once the followed kit has ended", async () => {
    const { user, sockets, kit } = openedElsewhere();
    await user.click(await screen.findByRole("button", { name: "Générer le kit" }));
    const stream = await openStream(sockets, "k7");
    expect(
      await screen.findByText(/Un kit est déjà en cours pour cette candidature/),
    ).toBeVisible();
    kit.arrive("cv", { content: "CV ciblé" });
    kit.finish();
    stream.push(councilEvents("k7").completed());
    expect(await screen.findByText(/Le kit est terminé/)).toBeVisible();
    expect(screen.queryByText(/Un kit est déjà en cours pour cette candidature/)).toBeNull();
  });

  it("follows the session that is already open on a 409 kit_in_progress", async () => {
    const { user, sockets } = openedElsewhere();
    await user.click(await screen.findByRole("button", { name: "Générer le kit" }));
    await openStream(sockets, "k7");
    expect(
      await screen.findByText(/Un kit est déjà en cours pour cette candidature/),
    ).toBeVisible();
  });
});
