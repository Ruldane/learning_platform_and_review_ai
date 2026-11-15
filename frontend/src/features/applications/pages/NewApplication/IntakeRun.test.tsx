import { QueryClient } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it } from "vitest";
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
        .join("|") || "fiche ouverte"}
    </p>
  );
}

async function setup() {
  server.use(...applicationsApi().handlers);
  const sockets = createFakeSocketServer();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(["applications", "list"], [applicationOut()]);
  const router = createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <IntakeRun sessionId="i1" createSocket={sockets.factory} onLeave={() => undefined} />
        ),
      },
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

  it("makes the applications read again when the session announces the fiche", async () => {
    const { client, router, stream, e } = await setup();
    stream.push(e.artifactReady("application", "a1", "/candidatures/a1"));
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
    expect(client.getQueryState(["applications", "list"])?.isInvalidated).toBe(true);
    expect(await screen.findByText("fiche ouverte")).toBeVisible();
  });

  it("hands the « même entreprise » information of the session to the opened fiche", async () => {
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
              "Pour info : tu as postulé chez Acme il y a 3 jours, pour le poste Autre poste.",
          },
        ],
      },
    } as typeof ready);
    await waitFor(() => expect(router.state.location.pathname).toBe("/candidatures/a1"));
    expect(
      await screen.findByText(/Pour info : tu as postulé chez Acme il y a 3 jours/),
    ).toBeVisible();
  });
});
