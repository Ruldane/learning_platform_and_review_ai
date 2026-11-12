import type { ComponentProps } from "react";
import type { useCouncilData } from "../../hooks/useCouncilData";
import type { useCouncilSession } from "../../hooks/useCouncilSession";
import type { ProposalsPane } from "./ProposalsPane";

const ANOTHER_ROUND = "another_round";
/** Question du choix du parcours (point d'arrêt n° 2). */
const CHOICE_KIND = "choose_path";

type Session = ReturnType<typeof useCouncilSession>;
type Data = ReturnType<typeof useCouncilData>;

/**
 * Ce que l'onglet Propositions reçoit. January ne peut choisir, mélanger ou relancer que tant que
 * le Conseil attend sa réponse à la question du choix ; « autre tour » suit les options de cette
 * question (elle n'en offre plus au plafond de tours : le bouton disparaît) et se fait par reprise.
 */
export function useProposalsPane(
  session: Session,
  data: Data,
  onShowBoard: (boardId: string) => void,
): ComponentProps<typeof ProposalsPane> {
  const { stream, actions } = session;
  const { proposals, choose } = data;
  const choice =
    stream.status === "waiting_user" && stream.pendingInterrupt?.kind === CHOICE_KIND
      ? stream.pendingInterrupt
      : null;
  const offersAnotherRound = choice?.options?.some((option) => option.value === ANOTHER_ROUND);
  return {
    proposals: proposals.data,
    loading: proposals.isPending,
    failed: proposals.isError,
    onRetry: () => void proposals.refetch(),
    canChoose: choice !== null,
    canAnotherRound: choice === null || offersAnotherRound === true,
    busy: choose.pending || actions.pending,
    notice: choose.notice,
    error: choose.error,
    onChoose: (id) => void choose.choose(id),
    onMix: (first, second) => void choose.choose(first, second),
    onAnotherRound: () => void actions.resume(choice?.interrupt_id ?? null, ANOTHER_ROUND),
    onShowBoard,
  };
}
