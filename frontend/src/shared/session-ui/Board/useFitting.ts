import type { ExcalidrawElement } from "@excalidraw/excalidraw/element/types";
import { useEffect, useRef, type RefObject } from "react";
import type { BoardApi } from "./boardApi";
import { REFIT_DELAY_MS, useRefitOnShow } from "./useRefitOnShow";

/** Frames the whole scene, leaving room for Excalidraw's toolbars (top and bottom). */
const FIT = {
  fitToViewport: true,
  viewportZoomFactor: 0.9,
  animate: false,
  canvasOffsets: { top: 72, bottom: 72, left: 16, right: 56 },
} as const;

interface Fitting {
  api: BoardApi | null;
  elements: readonly ExcalidrawElement[];
  /** The whole scene is shown and stable: one last fit to all its content. */
  settled: boolean;
  /** The canvas container, whose size drops to zero when the tab is hidden. */
  frame: RefObject<HTMLElement | null>;
  onReady: (api: BoardApi) => void;
}

/**
 * All the canvas fits: when the API arrives, once the scene is stable, right after the
 * first canvas measurement (an already seen state has no animation to fit afterwards), and when
 * a hidden tab becomes visible again.
 */
export function useFitting({ api, elements, settled, frame, onReady }: Fitting): void {
  const fitAll = () => api?.scrollToContent(undefined, FIT);
  useRefitOnShow(frame, fitAll);
  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  });

  useEffect(() => {
    if (!api) return;
    onReadyRef.current(api);
    api.scrollToContent(elements as ExcalidrawElement[], FIT);
  }, [api, elements]);

  useEffect(() => {
    if (api && settled) api.scrollToContent(undefined, FIT);
  }, [api, settled]);

  // The canvas is measured right after it is created: a fit done at that moment lands off.
  useEffect(() => {
    if (!api) return undefined;
    const timer = setTimeout(() => api.scrollToContent(undefined, FIT), REFIT_DELAY_MS);
    return () => clearTimeout(timer);
  }, [api]);
}
