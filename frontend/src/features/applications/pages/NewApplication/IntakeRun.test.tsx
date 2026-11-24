import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { applicationOut, applicationsApi } from "@/test/applicationsApi";
import { openStream } from "@/test/applicationsHarness";
import { councilEvents } from "@/test/councilEvents";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { IntakeRun } from "./IntakeRun";
import { openedInfo } from "../../navState";
import { useLocation } from "react-router";

function Landing() {
  const location = useLocation();
  return (
    <p>
      {openedInfo(location.state)
        .map((alert) => alert.message)
        .join("|") || "application opened"}
    </p>
  );
}

async function setup(stayMounted = false) {
  server.use(...applicationsApi().handlers);
  const sockets = createFakeSocketServer();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(["applications", "list"], [applicationOut()]);
  const intake = (
    <IntakeRun sessionId="i1" createSocket={sockets.factory} onLeave={() => undefined} />
  );
  const router = createMemoryRouter(
    // Keep the entry mounted after navigation to check that it handles the event once.
    stayMounted
      ? [{ path: "*", element: intake }]
      : [
          { path: "/", element: intake },
          { path: "/candidatures/:applicationId", element: <Landing /> },
        ],
    { initialEntries: ["/"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper(client) });
  const stream = await openStream(sockets, "i1");
  return { client, router, stream, e: councilEvents("i1") };
}

describe("IntakeRun", () => {
  beforeEach(() => useSessionStore.getState().reset("i1"));

  it("refreshes the application list when the session announces the application", async () => {
    const { client, router, stream, e } = await setup();
    stream.push(e.artifactReady("application", "a1", "/candidatures/a1"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
    expect(client.getQueryState(["applications", "list"])?.isInvalidated).toBe(true);
    expect(await screen.findByText("application opened")).toBeVisible();
  });

  it("passes other applications at the same company to the open application", async () => {
    const { router, stream, e } = await setup();
    const ready = e.artifactReady("application", "a1", "/candidatures/a1");
    stream.push({
      ...ready,
      payload: {
        ...ready.payload,
        info: [
          {
            application_id: "a9",
            company: "Acme",
            title: "Autre poste",
            status: "applied",
            message:
              "For reference, you applied for the Autre poste role at Acme 3 days ago.",
          },
        ],
      },
    } as typeof ready);
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
    expect(
      await screen.findByText(/you applied for the Autre poste role at Acme 3 days ago/),
    ).toBeVisible();
  });

  it("reads the applications once per announcing event, however many events follow", async () => {
    const { client, router, stream, e } = await setup(true);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    stream.push(e.artifactReady("application", "a1", "/candidatures/a1"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
    expect(invalidate).toHaveBeenCalledTimes(1);
    // Later session events still refer to the same announced application.
    stream.push(e.cost());
    stream.push(e.completed());
    await waitFor(() => expect(useSessionStore.getState().events["i1"]).toHaveLength(3));
    expect(invalidate).toHaveBeenCalledTimes(1);
  });
});
