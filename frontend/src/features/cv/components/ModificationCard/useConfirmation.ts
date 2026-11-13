import { useState } from "react";
import type { DecideOptions } from "../viewTypes";

/**
 * La confirmation d'une modification « à confirmer ». Elle vaut pour ce texte précis : si le texte
 * change (modification éditée, nouvelle proposition), elle est à refaire. Hors « à confirmer »,
 * rien à confirmer : `confirmed` est vrai et `opts` vide.
 */
export function useConfirmation(active: boolean, id: string, text: string) {
  const [confirmedFor, setConfirmedFor] = useState<string | null>(null);
  const current = `${id}:${text}`;
  const opts: DecideOptions = active ? { confirm: true } : {};
  return {
    confirmed: !active || confirmedFor === current,
    setConfirmed: (value: boolean) => setConfirmedFor(value ? current : null),
    opts,
  };
}
