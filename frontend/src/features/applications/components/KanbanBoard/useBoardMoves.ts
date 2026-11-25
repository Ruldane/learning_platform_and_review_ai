import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { ApplicationView, StatusView } from "../viewTypes";
import { statusName } from "./announcements";
import { useFocusAfterMove } from "./useFocusAfterMove";

/** Where a move comes from: the menu, a keyboard drag, or a mouse or touch drag. */
export type MoveSource = "menu" | "keyboard" | "pointer";

/**
 * Board moves: `move` ignores an unknown card or one already in the column; a
 * move from the menu is announced in the live region (`announcement`), drag and drop
 * is announced by dnd-kit. The menu and the keyboard return focus to the card (« Déplacer » or
 * handle) once it is in its new column; the mouse and touch leave it where it is.
 */
export function useBoardMoves(
  applications: ApplicationView[],
  onMove: (id: string, status: StatusView) => void,
) {
  const [announcement, setAnnouncement] = useState("");
  const { boardRef, moved } = useFocusAfterMove(applications);

  function move(id: string, status: StatusView, source: MoveSource) {
    const application = applications.find((item) => item.id === id);
    if (!application || application.status === status) return;
    if (source !== "pointer")
      moved(id, application.status, status, source === "menu" ? "menu" : "handle");
    if (source === "menu") {
      const values = { title: application.title, status: statusName(status) };
      setAnnouncement(t("applications.board.announce.moved", values));
    }
    onMove(id, status);
  }

  return { announcement, boardRef, move };
}
