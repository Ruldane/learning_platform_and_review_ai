import { useEffect, useState } from "react";

/**
 * Expected quiet after the last Excalidraw signal. Excalidraw adjusts the scene right after
 * receiving it (linked arrows recalculated, text measured, fonts applied) and reports these
 * changes with a slight delay: we let them pass before opening editing.
 */
export const QUIET_MS = 250;

/** `true` when the page's fonts are loaded (or when the browser cannot tell). */
function useFontsReady(): boolean {
  const [ready, setReady] = useState(() => typeof document.fonts === "undefined");
  useEffect(() => {
    if (typeof document.fonts === "undefined") return;
    let alive = true;
    void document.fonts.ready.then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);
  return ready;
}

/**
 * `true` once the whole scene is shown and stable: fonts are loaded
 * (`document.fonts.ready`) and Excalidraw has reported nothing for `QUIET_MS`. Only then
 * the canvas becomes editable and its changes count as January's. Each
 * change before that (`changeTick` grows on each signal) restarts the wait and becomes the
 * reference for edits, never an edit. Even without animation (seen state, reduced motion),
 * the canvas stays read-only for the length of this quiet period.
 */
export function useSettled(done: boolean, changeTick: number): boolean {
  const fontsReady = useFontsReady();
  const [settled, setSettled] = useState(false);
  useEffect(() => {
    if (!done || !fontsReady || settled) return;
    const timer = setTimeout(() => setSettled(true), QUIET_MS);
    return () => clearTimeout(timer);
  }, [done, fontsReady, settled, changeTick]);
  return settled;
}
