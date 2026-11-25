import { useEffect } from "react";

/** Ctrl+K on Windows and Linux, Cmd+K on Mac, with no other modifier. */
function isCaptureShortcut(event: KeyboardEvent): boolean {
  return (
    (event.ctrlKey || event.metaKey) &&
    !event.altKey &&
    !event.shiftKey &&
    !event.isComposing &&
    event.key.toLowerCase() === "k"
  );
}

/**
 * The global capture shortcut: Ctrl+K or Cmd+K opens the dialog wherever you are, including
 * inside an input field (capture is the app's global action, and Ctrl+K has no other use there).
 * The browser does not get the key (no search bar).
 */
export function useCaptureShortcut(onOpen: () => void) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!isCaptureShortcut(event)) return;
      event.preventDefault();
      onOpen();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpen]);
}
