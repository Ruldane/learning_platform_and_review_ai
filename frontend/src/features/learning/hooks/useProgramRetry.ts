import type { ProposalView } from "../types";
import { useChooseProposal } from "./useChooseProposal";

/**
 * Restarts the Strategist after its failure: the same choice (`POST /proposals/{id}/choose`,
 * one path or both of a mix) restarts it; `already_chosen` is false and the goal gives
 * the new program session. Its own `notice` and its own `error`, next to the button.
 * `retry` is `null` until the choice is known (proposals not yet read).
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
