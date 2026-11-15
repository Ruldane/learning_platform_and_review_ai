import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { KitPieceView, KitView } from "../types";

/** Une pièce vient d'arriver (ou d'être refaite par un nouveau lancement) : jamais celle de January. */
function arrived(before: KitPieceView | undefined, after: KitPieceView, running: boolean) {
  if (after.status === "pending" || after.edited || !before) return false;
  return before.status === "pending" || (running && before.updatedAt !== after.updatedAt);
}

function finishedSentence(pieces: KitPieceView[]): string {
  const count = (status: KitPieceView["status"]) =>
    pieces.filter((piece) => piece.status === status).length;
  const phrase = (
    key: "finishedReady" | "finishedCheck" | "finishedFailed",
    status: KitPieceView["status"],
  ) => {
    const n = count(status);
    return t(`applications.kitPage.${key}.${n === 1 ? "one" : "many"}`, { count: n });
  };
  return t("applications.kitPage.finished", {
    ready: phrase("finishedReady", "ready"),
    check: phrase("finishedCheck", "to_check"),
    failed: phrase("finishedFailed", "failed"),
  });
}

/** Ce que la relecture du kit apporte : les pièces arrivées, puis la fin du kit si elle vient d'avoir lieu. */
export function describeKitChange(before: KitView, after: KitView): string {
  const running = after.running || before.running;
  const sentences = after.pieces
    .filter((piece) =>
      arrived(
        before.pieces.find((old) => old.kind === piece.kind),
        piece,
        running,
      ),
    )
    .map((piece) =>
      t("applications.kitPage.arrived", {
        title: t(`applications.kitPiece.title.${piece.kind}`),
        status: t(`applications.kitPiece.arrivedAs.${piece.status}`),
      }),
    );
  if (before.running && !after.running) sentences.push(finishedSentence(after.pieces));
  return sentences.join(" ");
}

/**
 * La phrase à annoncer (zone vocale) quand une pièce arrive ou que le kit se termine. La première
 * lecture n'annonce rien : ce qui est déjà là n'est pas une arrivée. `count` change à chaque
 * annonce, même identique.
 */
export function useKitAnnouncement(kit: KitView | undefined): { message: string; count: number } {
  const [last, setLast] = useState<KitView | undefined>(undefined);
  const [spoken, setSpoken] = useState({ message: "", count: 0 });
  if (kit && kit !== last) {
    setLast(kit);
    const sentence = last ? describeKitChange(last, kit) : "";
    // Le compteur change à chaque annonce : une phrase identique est relue quand même.
    if (sentence) setSpoken({ message: sentence, count: spoken.count + 1 });
  }
  return spoken;
}
