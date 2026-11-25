import { useState } from "react";
import type { DecideOptions } from "../viewTypes";

/**
 * Confirmation of a modification marked « à confirmer ». It covers this exact text: if the text
 * changes (edited modification, new proposal), it must be given again. Outside « à confirmer »,
 * there is nothing to confirm: `confirmed` is true and `opts` is empty.
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
