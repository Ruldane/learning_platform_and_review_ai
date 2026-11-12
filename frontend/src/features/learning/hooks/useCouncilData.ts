import { useMemo } from "react";
import type { SessionEvent } from "@/shared/realtime/types";
import { sourcesFromEvents } from "@/shared/session-ui";
import { boardsFromEvents } from "../boardsFromEvents";
import { useBoardEdit } from "./useBoardEdit";
import { useBoards } from "./useBoards";
import { useChooseProposal } from "./useChooseProposal";
import { useProposals } from "./useProposals";

/** Identifiant du dernier événement de ce type, `null` s'il n'y en a pas. */
function lastIdOf(events: SessionEvent[], type: SessionEvent["type"]): string | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event?.type === type) return event.id;
  }
  return null;
}

/**
 * Ce que montre la zone de droite du Conseil : sources du direct, propositions (rechargées à
 * chaque `proposal.ready`), états du tableau (enregistrés puis du direct, sans doublon), et les
 * deux actions de January sur eux : choisir un parcours, retoucher le tableau.
 */
export function useCouncilData(goalId: string, sessionId: string, events: SessionEvent[]) {
  const sources = useMemo(() => sourcesFromEvents(events), [events]);
  const proposals = useProposals(goalId, lastIdOf(events, "proposal.ready"));
  const saved = useBoards(goalId, sessionId);
  const boards = useMemo(() => boardsFromEvents(saved.data ?? [], events), [saved.data, events]);
  const choose = useChooseProposal(goalId, sessionId);
  const edit = useBoardEdit(goalId);
  return { sources, proposals, saved, boards, choose, edit };
}
