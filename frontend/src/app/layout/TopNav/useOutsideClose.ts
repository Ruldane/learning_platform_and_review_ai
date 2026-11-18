import { useEffect, type RefObject } from "react";

/** Appelle `close` sur un clic hors de `ref` tant que `active` est vrai. */
export function useOutsideClose(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
  close: () => void,
): void {
  useEffect(() => {
    if (!active) return undefined;
    const onDown = (event: MouseEvent) => {
      if (event.target instanceof Node && !ref.current?.contains(event.target)) close();
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [ref, active, close]);
}
