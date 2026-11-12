import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { API, goalOut, sessionOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { openCouncil, renderCouncil, socketsOf } from "@/test/councilHarness";
import { server } from "@/test/server";
import { CouncilPage } from "./CouncilPage";

vi.mock(
  "@excalidraw/excalidraw",
  async () => (await import("@/shared/session-ui/Board/excalidrawMock")).module,
);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: vi.fn() }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const setup = (api: Parameters<typeof renderCouncil>[1] = {}) =>
  renderCouncil((createSocket) => <CouncilPage createSocket={createSocket} />, api);

describe("CouncilPage : programme", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("c1");
    useSessionStore.getState().reset("pr1");
  });
  afterEach(() => {
    useSessionStore.getState().reset("c1");
    useSessionStore.getState().reset("pr1");
  });

  it("follows the program session and links to the program once it is ready", async () => {
    const { fake } = setup({ goal: goalOut({ status: "chosen", program_session_id: "pr1" }) });
    server.use(
      http.get(`${API}/sessions/pr1`, () =>
        HttpResponse.json(sessionOut("pr1", "waiting_user", { graph: "program_builder" })),
      ),
    );
    const e = councilEvents("c1");
    (await openCouncil(fake)).push(e.message("moderator-choix", "Parcours choisi"), e.completed());
    expect(await screen.findByText("Le Stratège prépare ton programme…")).toBeInTheDocument();
    await waitFor(() => expect(socketsOf(fake, "pr1")).toHaveLength(1));
    const program = councilEvents("pr1");
    socketsOf(fake, "pr1")[0]!
      .open()
      .push(program.artifactReady("program", "pr9", "/apprendre/programme/pr9"));
    const link = await screen.findByRole("link", { name: "Voir le programme" });
    expect(link).toHaveAttribute("href", "/apprendre/programme/pr9");
    expect(document.querySelector('[aria-current="step"]')).toHaveTextContent("Programme");
  });

  it("finds the program again after a reload from the goal alone", async () => {
    const { fake } = setup({
      goal: goalOut({ status: "planned", program_id: "pr3", program_session_id: "pr1" }),
      status: "completed",
    });
    const e = councilEvents("c1");
    (await openCouncil(fake)).push(e.message("moderator-choix", "Parcours choisi"), e.completed());
    expect(await screen.findByRole("link", { name: "Voir le programme" })).toHaveAttribute(
      "href",
      "/apprendre/programme/pr3",
    );
  });

  it("polls the goal until the program session exists once the choice is announced", async () => {
    let reads = 0;
    const { fake } = setup();
    server.use(
      http.get(`${API}/goals/g1`, () => {
        reads += 1;
        return HttpResponse.json(
          reads < 3 ? goalOut() : goalOut({ status: "chosen", program_session_id: "pr1" }),
        );
      }),
      http.get(`${API}/sessions/pr1`, () =>
        HttpResponse.json(sessionOut("pr1", "running", { graph: "program_builder" })),
      ),
    );
    const e = councilEvents("c1");
    (await openCouncil(fake)).push(e.message("moderator-choix", "Parcours choisi"));
    await waitFor(() => expect(socketsOf(fake, "pr1")).toHaveLength(1), { timeout: 8000 });
  }, 12000);
});
