import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { fetchProposals } from "../api";
import { learningKeys } from "../queryKeys";
import { toProposalView } from "../toView";
import type { ProposalOut } from "../types";

const toViews = (proposals: ProposalOut[]) => proposals.map(toProposalView);

/**
 * Les propositions du dernier lot (`GET /goals/{id}/proposals`), rechargées à chaque nouveau
 * `proposal.ready` (`readyKey` : l'identifiant du dernier événement de ce type).
 */
export function useProposals(goalId: string, readyKey: string | null) {
  const query = useQuery({
    queryKey: learningKeys.proposals(goalId),
    queryFn: ({ signal }) => fetchProposals(goalId, signal),
    select: toViews,
  });
  const { refetch } = query;
  const seen = useRef(readyKey);
  useEffect(() => {
    if (readyKey === seen.current) return;
    seen.current = readyKey;
    void refetch();
  }, [readyKey, refetch]);
  return query;
}
