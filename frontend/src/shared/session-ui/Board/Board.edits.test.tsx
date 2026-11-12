import { act, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { BoardStateView } from "../boardTypes";
import { Board } from "./Board";
import {
  convertToExcalidrawElements,
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

const domainMap: BoardStateView = {
  id: "b1",
  kind: "domain_map",
  title: "Carte du domaine",
  step: 1,
  mermaid: "flowchart TD\n A[MLOps] --> B[Données]",
  scene: null,
  author: "scribe",
  createdAt: "2026-11-12T10:00:00Z",
};
const prerequisites: BoardStateView = {
  ...domainMap,
  id: "b3",
  kind: "prerequisites",
  title: "Prérequis",
  step: 2,
};
const shapes = [
  { id: "a", type: "rectangle", x: 0, y: 0 },
  { id: "b", type: "rectangle", x: 200, y: 0 },
  { id: "e", type: "arrow", x: 100, y: 20 },
];
/** Ce qu'Excalidraw signale au montage : flèche recalculée, formes décalées de quelques pixels. */
const normalized = (elements: { id: string }[]) =>
  elements.map((element) => {
    const shape = element as { x?: number; y?: number };
    return { ...element, x: (shape.x ?? 0) + 3, y: (shape.y ?? 0) + 2 };
  });
const annotated = [...shapes, { id: "t1", type: "text", x: 9, y: 9, text: "Docker" }];
const SEND = "Envoyer mes modifications aux agents";

function reducedMotion(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}

const editable = () =>
  waitFor(() =>
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "false"),
  );

function board(props: Partial<React.ComponentProps<typeof Board>> = {}) {
  return (
    <Board
      states={[domainMap]}
      activeId={null}
      onSelect={vi.fn()}
      onSendEdit={vi.fn()}
      sending={false}
      {...props}
    />
  );
}

describe("Board : retouches de January", () => {
  beforeEach(() => {
    resetExcalidrawMock();
    parse.mockReset();
    parse.mockResolvedValue({ elements: [{ type: "rectangle" }], files: {} });
    convertToExcalidrawElements.mockReturnValue(shapes);
    serializeAsJSON.mockReturnValue('{"type":"excalidraw","elements":[]}');
    fakeApi.getSceneElements.mockReturnValue(shapes);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("does not take Excalidraw's own adjustments for an edit (reduced motion)", async () => {
    reducedMotion(true);
    fake.mountChange = normalized;
    render(board());
    await screen.findByTestId("excalidraw");
    expect(screen.getByTestId("excalidraw")).toHaveAttribute("data-view-mode", "true");
    await waitFor(() => expect(fake.adjusted).toBe(1));
    await editable();
    const send = screen.getByRole("button", { name: SEND });
    expect(send).toBeDisabled();
    act(() => fake.props?.onChange?.(normalized(shapes), {}, {}));
    expect(send).toBeDisabled();
    act(() => fake.props?.onChange?.(normalized(annotated), {}, {}));
    expect(send).toBeEnabled();
  });

  it("does not take Excalidraw's own adjustments for an edit (a state already seen)", async () => {
    reducedMotion(false);
    const { rerender } = render(board({ states: [domainMap, prerequisites], activeId: "b1" }));
    await screen.findByTestId("excalidraw");
    await editable();
    rerender(board({ states: [domainMap, prerequisites], activeId: "b3" }));
    await editable();
    fake.mountChange = normalized;
    rerender(board({ states: [domainMap, prerequisites], activeId: "b1" }));
    await screen.findByRole("button", { name: /^Carte du domaine/, current: true });
    await waitFor(() => expect(fake.adjusted).toBe(1));
    await editable();
    expect(screen.getByRole("button", { name: SEND })).toBeDisabled();
  });

  it("keeps an unsent edit when the Scribe publishes a new state", async () => {
    reducedMotion(true);
    const { rerender } = render(board());
    await screen.findByTestId("excalidraw");
    await editable();
    act(() => fake.props?.onChange?.(annotated, {}, {}));
    expect(screen.getByRole("button", { name: SEND })).toBeEnabled();

    rerender(board({ states: [domainMap, prerequisites] }));
    const list = screen.getByRole("navigation", { name: "États du tableau" });
    expect(within(list).getByRole("button", { name: /^Carte du domaine/ })).toHaveAttribute(
      "aria-current",
      "true",
    );
    expect(within(list).getByRole("button", { name: /^Prérequis/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SEND })).toBeEnabled();
  });
});
