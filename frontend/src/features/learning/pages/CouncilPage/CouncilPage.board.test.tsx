import { act, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import {
  convertToExcalidrawElements,
  fake,
  fakeApi,
  resetExcalidrawMock,
  serializeAsJSON,
} from "@/shared/session-ui/Board/excalidrawMock";
import { API, boardOut, proposalOut } from "@/test/councilApi";
import { councilEvents } from "@/test/councilEvents";
import { apiError, openCouncil, renderCouncil } from "@/test/councilHarness";
import { server } from "@/test/server";
import { CouncilPage } from "./CouncilPage";

const parse = vi.fn();
vi.mock("@excalidraw/excalidraw", async () => {
  return (await import("@/shared/session-ui/Board/excalidrawMock")).module;
});
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: parse }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const shapes = [
  { id: "a", type: "rectangle", x: 0, y: 0 },
  { id: "a-t", type: "text", x: 0, y: 0, text: "MLOps", containerId: "a" },
];

const setup = (api: Parameters<typeof renderCouncil>[1] = {}) => {
  const { fake: fakeSockets, user } = renderCouncil(
    (createSocket) => <CouncilPage createSocket={createSocket} />,
    api,
  );
  return { fakeSockets, user };
};

const SEND = "Envoyer mes modifications aux agents";

/** Le canevas sort de la lecture seule une fois les ajustements d'Excalidraw passés. */
const editable = () =>
  waitFor(() =>
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "false"),
  );

describe("CouncilPage : tableau", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("c1");
    resetExcalidrawMock();
    parse.mockReset();
    parse.mockResolvedValue({ elements: [{ type: "rectangle" }], files: {} });
    convertToExcalidrawElements.mockReturnValue(shapes);
    serializeAsJSON.mockReturnValue('{"type":"excalidraw","elements":[]}');
    fakeApi.getSceneElements.mockReturnValue(shapes);
    // Mouvement réduit : le tableau apparaît d'un coup.
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });
  afterEach(() => {
    useSessionStore.getState().reset("c1");
    vi.unstubAllGlobals();
  });

  it("sends the board edits to the agents and lists the saved state", async () => {
    const edits: unknown[] = [];
    server.use(
      http.post(`${API}/boards/b1/edits`, async ({ request }) => {
        edits.push(await request.json());
        return HttpResponse.json(
          boardOut("b2", { author: "user", parent_id: "b1", title: "Ma version", step: 2 }),
          { status: 201 },
        );
      }),
    );
    const { fakeSockets, user } = setup({ boards: [boardOut("b1")], status: "running" });
    await openCouncil(fakeSockets);
    await screen.findByTestId("excalidraw");
    await editable();
    const send = screen.getByRole("button", { name: SEND });
    act(() => fake.props?.onChange?.(shapes, {}, {}));
    const edited = [
      ...shapes,
      { id: "t1", type: "text", x: 0, y: 0, text: "Docker", containerId: null, version: 2 },
    ];
    act(() => fake.props?.onChange?.(edited, {}, {}));
    await user.click(send);
    await waitFor(() =>
      expect(edits).toEqual([
        { scene: { type: "excalidraw", elements: [] }, note: "Ajouté : « Docker »" },
      ]),
    );
    expect(await screen.findByRole("button", { name: /Ma version/ })).toBeInTheDocument();
  });

  it("says so when the edits could not be sent, and keeps the button", async () => {
    server.use(
      http.post(`${API}/boards/b1/edits`, () =>
        HttpResponse.json(apiError("board_too_large", "Tableau trop volumineux."), {
          status: 413,
        }),
      ),
    );
    const { fakeSockets, user } = setup({ boards: [boardOut("b1")], status: "running" });
    await openCouncil(fakeSockets);
    await screen.findByTestId("excalidraw");
    await editable();
    act(() => fake.props?.onChange?.(shapes, {}, {}));
    act(() =>
      fake.props?.onChange?.(
        [...shapes, { id: "t1", type: "text", x: 9, y: 9, text: "Go" }],
        {},
        {},
      ),
    );
    await user.click(screen.getByRole("button", { name: SEND }));
    expect(await screen.findByText("Tableau trop volumineux.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SEND })).toBeEnabled();
    // Un seul message : celui du serveur, dans le volet (pas un second dans le tableau).
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });

  it("draws the Scribe's board as it arrives, once per board", async () => {
    const { fakeSockets } = setup({ status: "running" });
    const e = councilEvents();
    const socket = await openCouncil(fakeSockets);
    socket.push(e.boardUpdate("b1", 1), e.boardUpdate("b1", 1));
    await screen.findByTestId("excalidraw");
    expect(screen.getAllByRole("button", { name: /Carte du domaine/ })).toHaveLength(1);
    socket.push(e.boardUpdate("b2", 2, { kind: "prerequisites", title: "Prérequis" }));
    expect(await screen.findByRole("button", { name: /Prérequis/ })).toBeInTheDocument();
  });

  it("shows a proposal on the board from its card", async () => {
    const { fakeSockets, user } = setup({
      boards: [
        boardOut("b1"),
        boardOut("b3", { kind: "comparison", title: "Comparaison", step: 3 }),
      ],
      proposals: [proposalOut("p1", 1, { board_id: "b3" }), proposalOut("p2", 2)],
      status: "waiting_user",
    });
    await openCouncil(fakeSockets);
    await user.click(await screen.findByRole("tab", { name: "Propositions" }));
    await user.click(await screen.findByRole("button", { name: "Voir « Parcours 1 » au tableau" }));
    expect(screen.getByRole("tab", { name: "Tableau", selected: true })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Comparaison/ })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });
});
