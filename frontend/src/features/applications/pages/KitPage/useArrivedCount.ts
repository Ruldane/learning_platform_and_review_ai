import { useState } from "react";
import type { KitPieceView } from "../../types";

/**
 * Les pièces arrivées pendant ce lancement. Au lancement vu de cette page, on note la date de chaque
 * pièce déjà rangée : une relance ne compte pas « 7 sur 7 » avant d'avoir refait quoi que ce soit.
 * Une pièce modifiée par January est gardée telle quelle : elle est déjà là. Une page ouverte
 * pendant un kit en cours n'a pas vu le lancement : elle compte toutes les pièces rangées.
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
