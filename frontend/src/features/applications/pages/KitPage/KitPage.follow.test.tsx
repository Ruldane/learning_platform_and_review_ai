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

describe("KitPage, following a running kit", () => {
  beforeEach(() => useSessionStore.getState().reset("k1"));

  it("follows a kit that is already running when the page opens, without starting another", async () => {
    const { sockets, kit } = setup({
      running: true,
      sessionId: "k9",
      items: [kitItem("cv")],
    });
    await openStream(sockets, "k9");
    expect(kit.state.starts).toBe(0);
    expect(await screen.findByText(/The kit is being prepared/)).toBeVisible();
    expect((await piece("Tailored résumé")).textContent).toContain("Ready");
    expect((await piece("Cover letter")).textContent).toContain("Preparing");
  });

  /** A kit starts elsewhere between loading the page and clicking Generate. */
  function openedElsewhere() {
    const box: { kit?: ReturnType<typeof setup>["kit"] } = {};
    const start = () => {
      if (box.kit) {
        box.kit.state.running = true;
        box.kit.state.sessionId = "k7";
      }
      return HttpResponse.json(
        apiError("kit_in_progress", "A kit is already in progress.", { session_id: "k7" }),
        { status: 409 },
      );
    };
    const view = setup({ start });
    box.kit = view.kit;
    return view;
  }

  it("removes the note about following a kit after the run ends", async () => {
    const { user, sockets, kit } = openedElsewhere();
    await user.click(await screen.findByRole("button", { name: "Generate the kit" }));
    const stream = await openStream(sockets, "k7");
    expect(
      await screen.findByText(/A kit is already in progress for this application/),
    ).toBeVisible();
    kit.arrive("cv", { content: "CV ciblé" });
    kit.finish();
    stream.push(councilEvents("k7").completed());
    expect(await screen.findByText(/The kit is done/)).toBeVisible();
    expect(screen.queryByText(/A kit is already in progress for this application/)).toBeNull();
  });

  it("follows the session that is already open on a 409 kit_in_progress", async () => {
    const { user, sockets } = openedElsewhere();
    await user.click(await screen.findByRole("button", { name: "Generate the kit" }));
    await openStream(sockets, "k7");
    expect(
      await screen.findByText(/A kit is already in progress for this application/),
    ).toBeVisible();
  });
});
