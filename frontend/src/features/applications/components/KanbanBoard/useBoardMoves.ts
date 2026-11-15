import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { ApplicationView, StatusView } from "../viewTypes";
import { statusName } from "./announcements";
import { useFocusAfterMove } from "./useFocusAfterMove";

/**
 * Les déplacements du tableau : `move` ignore une carte inconnue ou déjà dans la colonne ; un
 * déplacement par le menu est annoncé dans la zone vocale (`announcement`) et rend le focus à la
 * carte une fois dans sa nouvelle colonne ; celui du glisser-déposer est annoncé par dnd-kit.
 */
export function useBoardMoves(
  applications: ApplicationView[],
  onMove: (id: string, status: StatusView) => void,
) {
  const [announcement, setAnnouncement] = useState("");
  const { boardRef, moved } = useFocusAfterMove(applications);

  function move(id: string, status: StatusView, viaMenu: boolean) {
    const application = applications.find((item) => item.id === id);
    if (!application || application.status === status) return;
    if (viaMenu) {
      moved(id);
      const values = { title: application.title, status: statusName(status) };
      setAnnouncement(t("applications.board.announce.moved", values));
    }
    onMove(id, status);
  }

  return { announcement, boardRef, move };
}
