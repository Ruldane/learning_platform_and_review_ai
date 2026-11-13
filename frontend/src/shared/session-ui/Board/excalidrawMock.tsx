/**
 * Faux `@excalidraw/excalidraw` pour les tests du tableau : jsdom n'a ni canevas ni polices.
 * Usage : `vi.mock("@excalidraw/excalidraw", async () => (await import("./excalidrawMock")).module)`.
 */
import { act } from "@testing-library/react";
import { useEffect, useLayoutEffect, useRef } from "react";
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

export const fake: {
  props: FakeExcalidrawProps | null;
  /**
   * Ajustements d'Excalidraw au montage (flèches liées recalculées, texte mesuré) : la scène
   * qu'il signale aussitôt, à partir des éléments reçus. `null` : aucun `onChange` au montage.
   */
  mountChange: ((elements: { id: string }[]) => unknown[]) | null;
  /** Nombre d'ajustements de montage déjà signalés. */
  adjusted: number;
  /**
   * Comme le vrai `componentDidUpdate` d'Excalidraw : `onChange` à chaque mise à jour du composant
   * (nouvelles props comprises), avec la scène du moment, même inchangée.
   */
  changeOnUpdate: boolean;
} = { props: null, mountChange: null, adjusted: 0, changeOnUpdate: false };

function Excalidraw(props: FakeExcalidrawProps) {
  const mounted = useRef(false);
  useEffect(() => {
    fake.props = props;
  });
  useLayoutEffect(() => {
    if (mounted.current && fake.changeOnUpdate)
      props.onChange?.(props.initialData?.elements ?? [], {}, {});
    mounted.current = true;
  });
  useEffect(() => {
    props.excalidrawAPI?.(fakeApi);
    const adjust = fake.mountChange;
    // Comme Excalidraw : un peu après le montage (polices chargées), avec les props du moment.
    const timer = adjust
      ? setTimeout(() => {
          act(() => fake.props?.onChange?.(adjust(props.initialData?.elements ?? []), {}, {}));
          fake.adjusted += 1;
        })
      : undefined;
    return () => clearTimeout(timer);
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
  fake.mountChange = null;
  fake.adjusted = 0;
  fake.changeOnUpdate = false;
  for (const fn of Object.values(fakeApi)) fn.mockClear();
  exportToBlob.mockReset();
  exportToSvg.mockReset();
  serializeAsJSON.mockReset();
  convertToExcalidrawElements.mockReset();
}
