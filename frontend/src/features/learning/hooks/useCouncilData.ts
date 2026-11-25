import { useMemo } from "react";
import type { SessionEvent } from "@/shared/realtime/types";
import { sourcesFromEvents } from "@/shared/session-ui";
import { boardsFromEvents } from "../boardsFromEvents";
import { useBoardEdit } from "./useBoardEdit";
import { useBoards } from "./useBoards";
import { useChooseProposal } from "./useChooseProposal";
import { useProposals } from "./useProposals";

/** Id of the last event of this type, `null` if there is none. */
function lastIdOf(events: SessionEvent[], type: SessionEvent["type"]): string | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event?.type === type) return event.id;
  }
  return null;
}

/**
 * What the Council's right area shows: live sources, proposals (reloaded on
 * each `proposal.ready`), board states (saved, then live, no duplicates), and the
 * two January actions on them: choose a path, edit the board.
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
