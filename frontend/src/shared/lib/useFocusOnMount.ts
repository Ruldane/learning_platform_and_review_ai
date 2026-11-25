import { useEffect, useRef } from "react";

/**
 * Moves focus to an element (a heading with `tabIndex={-1}`) when it appears to replace
 * the one that had it: otherwise, unmounting the clicked button sends focus to `body` and
 * a keyboard user starts again from the top of the page. Acts once, when `enabled` turns true,
 * never on a simple page load.
 */
export function useFocusOnMount<T extends HTMLElement>(enabled: boolean) {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (enabled) ref.current?.focus();
  }, [enabled]);
  return ref;
}
