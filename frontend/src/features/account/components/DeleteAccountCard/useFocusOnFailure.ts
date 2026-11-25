import { useEffect, useRef } from "react";

/** A ref to attach to the failure message: it receives focus on each new failure. */
export function useFocusOnFailure(failure: object | null) {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (failure) ref.current?.focus();
  }, [failure]);
  return ref;
}
