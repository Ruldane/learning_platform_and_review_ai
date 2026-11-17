import { useEffect, useRef } from "react";

/** Une référence à poser sur le message d'échec : il reçoit le focus à chaque nouvel échec. */
export function useFocusOnFailure(failure: object | null) {
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (failure) ref.current?.focus();
  }, [failure]);
  return ref;
}
