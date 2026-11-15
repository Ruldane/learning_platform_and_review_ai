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
  return t("applications.kitPage.finished", {
    ready: count("ready"),
    check: count("to_check"),
    failed: count("failed"),
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
 * lecture n'annonce rien : ce qui est déjà là n'est pas une arrivée.
 */
export function useKitAnnouncement(kit: KitView | undefined): string {
  const [last, setLast] = useState<KitView | undefined>(undefined);
  const [message, setMessage] = useState("");
  if (kit && kit !== last) {
    setLast(kit);
    const sentence = last ? describeKitChange(last, kit) : "";
    if (sentence) setMessage(sentence);
  }
  return message;
}
