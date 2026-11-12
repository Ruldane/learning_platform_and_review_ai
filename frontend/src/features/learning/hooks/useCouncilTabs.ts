import { useState } from "react";
import type { CouncilStage, CouncilTab } from "../components/viewTypes";

/**
 * L'onglet ouvert de la zone de droite et l'état du tableau regardé. Quand le Conseil arrive aux
 * propositions, l'onglet Propositions s'ouvre (une seule fois par arrivée : January peut ensuite
 * aller où il veut). « Voir au tableau » ouvre le tableau sur l'état demandé.
 */
export function useCouncilTabs(stage: CouncilStage) {
  const [tab, setTab] = useState<CouncilTab>(stage === "proposals" ? "proposals" : "board");
  const [boardId, setBoardId] = useState<string | null>(null);
  const [seenStage, setSeenStage] = useState(stage);
  // État dérivé du rendu (pas d'effet) : on change d'étape, on ouvre les propositions.
  if (seenStage !== stage) {
    setSeenStage(stage);
    if (stage === "proposals") setTab("proposals");
  }
  const showBoard = (id: string) => {
    setBoardId(id);
    setTab("board");
  };
  return { tab, setTab, boardId, setBoardId, showBoard };
}
