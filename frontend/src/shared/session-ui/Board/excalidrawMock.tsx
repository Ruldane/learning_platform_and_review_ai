/**
 * Fake `@excalidraw/excalidraw` for board tests: jsdom has no canvas or fonts.
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
   * Excalidraw's adjustments on mount (linked arrows recalculated, text measured): the scene
   * it reports at once, from the elements received. `null`: no `onChange` on mount.
   */
  mountChange: ((elements: { id: string }[]) => unknown[]) | null;
  /** Number of mount adjustments already reported. */
  adjusted: number;
  /**
   * Like Excalidraw's real `componentDidUpdate`: `onChange` on each component update
   * (new props included), with the current scene, even if unchanged.
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
    // Like Excalidraw: a little after mount (fonts loaded), with the current props.
    const timer = adjust
      ? setTimeout(() => {
          act(() => fake.props?.onChange?.(adjust(props.initialData?.elements ?? []), {}, {}));
          fake.adjusted += 1;
        })
      : undefined;
    return () => clearTimeout(timer);
    // Excalidraw only exposes its API once mounted.
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

/** The elements of the last scene update sent to the canvas. */
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
