import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { KitPieceView, KitView } from "../types";

/** A piece has just arrived (or been redone by a new run): never January's own. */
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

/** What the kit re-read brings: the pieces that arrived, then the end of the kit if it has just
 * happened. */
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
 * The sentence to announce (live region) when a piece arrives or the kit ends. The first
 * read announces nothing: what is already there is not an arrival. `count` changes on each
 * announcement, even an identical one.
 */
export function useKitAnnouncement(kit: KitView | undefined): { message: string; count: number } {
  const [last, setLast] = useState<KitView | undefined>(undefined);
  const [spoken, setSpoken] = useState({ message: "", count: 0 });
  if (kit && kit !== last) {
    setLast(kit);
    const sentence = last ? describeKitChange(last, kit) : "";
    // The counter changes on each announcement: an identical sentence is still read.
    if (sentence) setSpoken({ message: sentence, count: spoken.count + 1 });
  }
  return spoken;
}
