import { useEffect, useRef } from "react";

/**
 * Rend le focus à un élément (un titre à `tabIndex={-1}`) quand il apparaît pour remplacer celui
 * qui l'avait : sans cela, démonter le bouton cliqué envoie le focus sur `body` et la personne au
 * clavier repart du haut de la page. N'agit qu'une fois, quand `enabled` devient vrai, jamais au
 * simple chargement d'une page.
 */
export function useFocusOnMount<T extends HTMLElement>(enabled: boolean) {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (enabled) ref.current?.focus();
  }, [enabled]);
  return ref;
}
