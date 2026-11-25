import { useState } from "react";
import type { KitPieceView } from "../../types";

/**
 * The pieces that arrived during this launch. For a launch seen from this page, the date of each
 * piece already filed is noted: a re-run does not count « 7 sur 7 » until something is redone.
 * A piece edited by January is kept as is: it is already there. A page opened
 * during a running kit did not see the launch: it counts all filed pieces.
 */
export function useArrivedCount(pieces: KitPieceView[], running: boolean): number {
  const [wasRunning, setWasRunning] = useState(running);
  const [before, setBefore] = useState<Record<string, string | null> | null>(null);
  if (running !== wasRunning) {
    setWasRunning(running);
    setBefore(running ? Object.fromEntries(pieces.map((p) => [p.kind, p.updatedAt])) : null);
  }
  return pieces.filter(
    (piece) =>
      piece.status !== "pending" &&
      (piece.edited || before === null || piece.updatedAt !== before[piece.kind]),
  ).length;
}
