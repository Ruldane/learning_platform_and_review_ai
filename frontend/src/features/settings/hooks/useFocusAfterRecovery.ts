import { useEffect, useRef } from "react";

/**
 * Gives focus back to the element of `ref` when a read that had failed succeeds: the button
 * « Réessayer » clicked is unmounted with the error; without this, focus falls to `body`.
 * Never acts on a plain load, nor when nothing had failed.
 */
export function useFocusAfterRecovery<T extends HTMLElement>(failed: boolean) {
  const ref = useRef<T>(null);
  const hadFailed = useRef(false);
  useEffect(() => {
    if (failed) {
      hadFailed.current = true;
    } else if (hadFailed.current) {
      hadFailed.current = false;
      ref.current?.focus();
    }
  }, [failed]);
  return ref;
}
