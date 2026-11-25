import { useState } from "react";
import type { CouncilStage, CouncilTab } from "../components/viewTypes";

/**
 * The open tab of the right area and the board state being viewed. When the Council reaches
 * proposals, the Propositions tab opens (once per arrival: January can then
 * go wherever they want). « Voir au tableau » opens the board on the requested state.
 */
export function useCouncilTabs(stage: CouncilStage) {
  const [tab, setTab] = useState<CouncilTab>(stage === "proposals" ? "proposals" : "board");
  const [boardId, setBoardId] = useState<string | null>(null);
  const [seenStage, setSeenStage] = useState(stage);
  // State derived during render (no effect): on a stage change, the proposals open.
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
