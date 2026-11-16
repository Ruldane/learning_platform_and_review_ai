import { useState } from "react";

export type CopyState = "idle" | "copied" | "failed";

/** L'état de la copie est celui d'une relance : une autre relance repart de zéro. */
interface CopyOf {
  reminderId: string;
  state: CopyState;
}

/** Copier le brouillon d'une relance (l'application n'envoie rien) et garder le résultat de la copie. */
export function useCopyState(
  reminderId: string,
  draft: string,
  onCopy: (draft: string) => void | Promise<void>,
) {
  const [last, setLast] = useState<CopyOf | null>(null);
  const state: CopyState = last?.reminderId === reminderId ? last.state : "idle";

  async function copy() {
    try {
      await onCopy(draft);
      setLast({ reminderId, state: "copied" });
    } catch {
      setLast({ reminderId, state: "failed" });
    }
  }

  return { state, copy };
}
