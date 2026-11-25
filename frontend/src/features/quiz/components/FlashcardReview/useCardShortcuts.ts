import { useEffect } from "react";

interface Shortcuts {
  /** Ignores everything: a send is in flight. */
  busy: boolean;
  flipped: boolean;
  onReveal: () => void;
  onResult: (result: "ok" | "fail") => void;
}

function inTextField(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable;
}

function onControl(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && target.closest("button, a, summary") !== null;
}

/**
 * Card shortcuts: Space shows the answer, then 1 (« Raté ») and 2 (« Su »). They live on
 * the window so they work without focus on the card, but they yield to a text field, to a
 * combined key (Ctrl, Cmd, Alt) and, for Space only, to a button, link or summary that has
 * focus: Space is already its own click there.
 */
export function useCardShortcuts({ busy, flipped, onReveal, onResult }: Shortcuts) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (busy || event.repeat || event.ctrlKey || event.metaKey || event.altKey) return;
      if (inTextField(event.target)) return;
      if (event.key === " ") {
        if (flipped || onControl(event.target)) return;
        event.preventDefault();
        onReveal();
      } else if (flipped && event.key === "1") {
        onResult("fail");
      } else if (flipped && event.key === "2") {
        onResult("ok");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, flipped, onReveal, onResult]);
}
