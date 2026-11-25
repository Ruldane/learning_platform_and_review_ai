import { useEffect, useRef, type RefObject } from "react";

/** Excalidraw measures its container in turn: leave it that time before fitting. */
export const REFIT_DELAY_MS = 100;

/**
 * Fits the content when the canvas becomes visible again. A hidden tab brings its container back to
 * zero size: any fit done at that moment (new Scribe state, resized window) is
 * wrong. As soon as the area has a size again, `refit` fits. A size that changes without passing
 * through zero does not refit: January keeps the zoom and position they chose.
 */
export function useRefitOnShow(frame: RefObject<HTMLElement | null>, refit: () => void): void {
  const latest = useRef(refit);
  useEffect(() => {
    latest.current = refit;
  });

  useEffect(() => {
    const element = frame.current;
    if (!element || typeof ResizeObserver === "undefined") return undefined;
    let hidden = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new ResizeObserver((entries) => {
      const box = entries.at(-1)?.contentRect;
      if (!box) return;
      const empty = box.width === 0 || box.height === 0;
      if (!empty && hidden) {
        clearTimeout(timer);
        timer = setTimeout(() => latest.current(), REFIT_DELAY_MS);
      }
      hidden = empty;
    });
    observer.observe(element);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, [frame]);
}
