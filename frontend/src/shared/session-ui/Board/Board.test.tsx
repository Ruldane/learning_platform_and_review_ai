import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import mermaid from "mermaid";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { BoardStateView } from "../boardTypes";
import { Board } from "./Board";
import {
  convertToExcalidrawElements,
  exportToBlob,
  exportToSvg,
  fake,
  fakeApi,
  resetExcalidrawMock,
  serializeAsJSON,
} from "./excalidrawMock";

const parse = vi.fn();
vi.mock("@excalidraw/excalidraw", async () => (await import("./excalidrawMock")).module);
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("@excalidraw/mermaid-to-excalidraw", () => ({ parseMermaidToExcalidraw: parse }));
vi.mock("mermaid", () => ({ default: { initialize: vi.fn(), render: vi.fn() } }));

const scribeState: BoardStateView = {
  id: "b1",
  kind: "domain_map",
  title: "Carte du domaine",
  step: 1,
  mermaid: "flowchart TD\n A[MLOps] --> B[Données]",
  scene: null,
  author: "scribe",
  createdAt: "2026-11-12T10:00:00Z",
};
const userState: BoardStateView = {
  ...scribeState,
  id: "b2",
  title: "Ma version",
  step: 2,
  author: "user",
  scene: { elements: [{ id: "u1", type: "rectangle" }], files: {} },
};
const shapes = [
  { id: "a", type: "rectangle", x: 0, y: 0 },
  { id: "a-t", type: "text", x: 0, y: 0, text: "MLOps", containerId: "a" },
];

function renderBoard(props: Partial<React.ComponentProps<typeof Board>> = {}) {
  const onSendEdit = vi.fn();
  const onSelect = vi.fn();
  const view = render(
    <Board
      states={[scribeState, userState]}
      activeId="b1"
      onSelect={onSelect}
      onSendEdit={onSendEdit}
      sending={false}
      {...props}
    />,
  );
  return { onSendEdit, onSelect, ...view };
}

describe("Board", () => {
  beforeEach(() => {
    resetExcalidrawMock();
    parse.mockReset();
    parse.mockResolvedValue({ elements: [{ type: "rectangle" }], files: {} });
    convertToExcalidrawElements.mockReturnValue(shapes);
    serializeAsJSON.mockReturnValue('{"type":"excalidraw","elements":[]}');
    fakeApi.getSceneElements.mockReturnValue(shapes);
    vi.mocked(mermaid.initialize).mockClear();
    vi.mocked(mermaid.render).mockResolvedValue({ svg: "<svg></svg>", diagramType: "flowchart" });
    // Mouvement réduit : le tableau apparaît d'un coup, sans attendre les 200 ms.
    vi.stubGlobal("matchMedia", (query: string) => ({
      matches: true,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("renders the fallback with strict security when conversion fails", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    parse.mockRejectedValue(new Error("Parse error near A[MLOps]"));
    renderBoard();
    expect(await screen.findByRole("img", { name: "Schéma : Carte du domaine" })).toBeVisible();
    expect(mermaid.initialize).toHaveBeenCalledWith(
      expect.objectContaining({ securityLevel: "strict" }),
    );
    expect(error).toHaveBeenCalledWith("board_fallback", { boardId: "b1" });
    // Jamais le code Mermaid ni le message de l'analyseur dans le journal.
    expect(JSON.stringify(error.mock.calls)).not.toContain("MLOps");
    expect(screen.queryByTestId("excalidraw")).not.toBeInTheDocument();
    error.mockRestore();
  });

  it("shows a user scene as it is, without converting the Mermaid", async () => {
    renderBoard({ activeId: "b2" });
    await screen.findByTestId("excalidraw");
    expect(parse).not.toHaveBeenCalled();
    expect(fake.props?.initialData?.elements).toEqual([{ id: "u1", type: "rectangle" }]);
  });

  it("sends edits with the computed note", async () => {
    const user = userEvent.setup();
    const { onSendEdit } = renderBoard();
    await screen.findByTestId("excalidraw");
    const send = screen.getByRole("button", { name: "Envoyer mes modifications aux agents" });
    expect(send).toBeDisabled();

    act(() => fake.props?.onChange?.(shapes, {}, {}));
    expect(send).toBeDisabled();
    const edited = [
      ...shapes,
      { id: "t1", type: "text", x: 0, y: 0, text: "Docker", containerId: null, version: 2 },
    ];
    act(() => fake.props?.onChange?.(edited, {}, {}));
    expect(send).toBeEnabled();

    await user.click(send);
    expect(onSendEdit).toHaveBeenCalledWith("b1", {
      scene: expect.any(Object),
      note: "Ajouté : « Docker »",
    });
    await waitFor(() => expect(send).toBeDisabled());
  });

  it("exports PNG, SVG and .excalidraw", async () => {
    const user = userEvent.setup();
    URL.createObjectURL = vi.fn(() => "blob:fake");
    URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    exportToBlob.mockResolvedValue(new Blob(["png"]));
    exportToSvg.mockResolvedValue(document.createElementNS("http://www.w3.org/2000/svg", "svg"));
    renderBoard();
    await screen.findByTestId("excalidraw");

    await user.click(await screen.findByRole("button", { name: "Exporter en PNG" }));
    await user.click(screen.getByRole("button", { name: "Exporter en SVG" }));
    await user.click(screen.getByRole("button", { name: "Exporter (.excalidraw)" }));
    await waitFor(() => expect(serializeAsJSON).toHaveBeenCalled());
    expect(exportToBlob).toHaveBeenCalled();
    expect(exportToSvg).toHaveBeenCalled();
  });

  it("tells the user when an export fails", async () => {
    const user = userEvent.setup();
    exportToBlob.mockRejectedValue(new Error("canvas"));
    renderBoard();
    await screen.findByTestId("excalidraw");
    await user.click(await screen.findByRole("button", { name: "Exporter en PNG" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("L'export a échoué");
  });

  it("keyboard: state list and toolbar are reachable and labelled", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderBoard();
    await screen.findByTestId("excalidraw");
    const list = screen.getByRole("navigation", { name: "États du tableau" });
    const first = within(list).getByRole("button", { name: /^Carte du domaine Carte/ });
    expect(first).toHaveAccessibleName("Carte du domaine Carte du domaine · Scribe");
    expect(first).toHaveAttribute("aria-current", "true");
    expect(within(list).getByRole("button", { name: /^Ma version/ })).toHaveTextContent("Toi");

    await user.tab();
    expect(first).toHaveFocus();
    await user.tab();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("b2");

    const toolbar = screen.getByRole("toolbar", { name: "Actions du tableau" });
    await waitFor(() =>
      expect(within(toolbar).getByRole("button", { name: "Exporter en PNG" })).toBeEnabled(),
    );
    await user.tab();
    expect(within(toolbar).getByRole("button", { name: "Exporter en PNG" })).toHaveFocus();
  });

  it("hides the send button on a read-only board", async () => {
    renderBoard({ readOnly: true });
    await screen.findByTestId("excalidraw");
    expect(screen.queryByRole("button", { name: /Envoyer mes modifications/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Exporter en PNG" })).toBeInTheDocument();
  });

  it("shows an empty state without any board state", () => {
    renderBoard({ states: [], activeId: null });
    expect(screen.getByText("Le Scribe n'a encore rien dessiné.")).toBeInTheDocument();
  });

  it("falls back to the latest state when the active one is unknown", async () => {
    renderBoard({ activeId: "inconnu" });
    await screen.findByTestId("excalidraw");
    expect(fake.props?.initialData?.elements).toEqual([{ id: "u1", type: "rectangle" }]);
  });
});
