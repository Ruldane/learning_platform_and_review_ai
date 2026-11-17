import { useEffect, useRef } from "react";

/**
 * Rend le focus à l'élément de `ref` quand une lecture qui avait échoué réussit : le bouton
 * « Réessayer » cliqué est démonté avec l'erreur, et sans cela le focus tomberait sur `body`.
 * N'agit jamais au simple chargement, ni quand rien n'avait échoué.
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
