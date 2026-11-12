import type { ProposalView } from "../types";
import { useChooseProposal } from "./useChooseProposal";

/**
 * Relance du Stratège après son échec : le même choix (`POST /proposals/{id}/choose`, un parcours
 * ou les deux du mélange) le relance, le back répond `already_chosen` faux et l'objectif relu donne
 * la nouvelle session du programme. Son propre `notice` et sa propre `error`, à côté du bouton.
 * `retry` vaut `null` tant que le choix n'est pas connu (propositions pas encore lues).
 */
export function useProgramRetry(
  goalId: string,
  sessionId: string,
  proposals: ProposalView[] | undefined,
) {
  const choose = useChooseProposal(goalId, sessionId);
  const [first, second] = (proposals ?? []).filter((proposal) => proposal.chosen);
  const retry = first ? () => void choose.choose(first.id, second?.id ?? null) : null;
  return { retry, pending: choose.pending, notice: choose.notice, error: choose.error };
}
