import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { ApplicationView, StatusView } from "../viewTypes";
import { statusName } from "./announcements";
import { useFocusAfterMove } from "./useFocusAfterMove";

/** D'où vient un déplacement : le menu, un glisser au clavier ou un glisser à la souris ou au doigt. */
export type MoveSource = "menu" | "keyboard" | "pointer";

/**
 * Les déplacements du tableau : `move` ignore une carte inconnue ou déjà dans la colonne ; un
 * déplacement par le menu est annoncé dans la zone vocale (`announcement`), celui du glisser-déposer
 * l'est par dnd-kit. Le menu et le clavier rendent le focus à la carte (bouton « Déplacer » ou
 * poignée) une fois dans sa nouvelle colonne ; la souris et le doigt le laissent où il est.
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
