/**
 * Faux `@excalidraw/excalidraw` pour les tests du tableau : jsdom n'a ni canevas ni polices.
 * Usage : `vi.mock("@excalidraw/excalidraw", async () => (await import("./excalidrawMock")).module)`.
 */
import { useEffect } from "react";
import { vi } from "vitest";

export interface FakeExcalidrawProps {
  excalidrawAPI?: (api: unknown) => void;
  initialData?: { elements: { id: string }[]; files?: unknown };
  viewModeEnabled?: boolean;
  onChange?: (elements: unknown[], appState: unknown, files: unknown) => void;
}

export const fakeApi = {
  updateScene: vi.fn(),
  addFiles: vi.fn(),
  scrollToContent: vi.fn(),
  getSceneElements: vi.fn((): unknown[] => []),
  getAppState: vi.fn(() => ({})),
  getFiles: vi.fn(() => ({})),
};

export const fake: { props: FakeExcalidrawProps | null } = { props: null };

function Excalidraw(props: FakeExcalidrawProps) {
  useEffect(() => {
    fake.props = props;
  });
  useEffect(() => {
    props.excalidrawAPI?.(fakeApi);
    // Excalidraw ne rend son API qu'une fois monté.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <div data-testid="excalidraw" data-view-mode={String(props.viewModeEnabled)} />;
}

export const exportToBlob = vi.fn();
export const exportToSvg = vi.fn();
export const serializeAsJSON = vi.fn();
export const convertToExcalidrawElements = vi.fn();

export const module = {
  Excalidraw,
  CaptureUpdateAction: { NEVER: "NEVER" },
  exportToBlob,
  exportToSvg,
  serializeAsJSON,
  convertToExcalidrawElements,
};

/** Les éléments de la dernière mise à jour de scène envoyée au canevas. */
export function lastSceneIds(): string[] {
  const call = fakeApi.updateScene.mock.calls.at(-1)?.[0] as { elements: { id: string }[] };
  return call.elements.map((element) => element.id);
}

export function resetExcalidrawMock(): void {
  fake.props = null;
  for (const fn of Object.values(fakeApi)) fn.mockClear();
  exportToBlob.mockReset();
  exportToSvg.mockReset();
  serializeAsJSON.mockReset();
  convertToExcalidrawElements.mockReset();
}
