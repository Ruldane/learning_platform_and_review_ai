import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { fetchProposals } from "../api";
import { learningKeys } from "../queryKeys";
import { toProposalView } from "../toView";
import type { ProposalOut } from "../types";

const toViews = (proposals: ProposalOut[]) => proposals.map(toProposalView);

/**
 * The proposals of the latest batch (`GET /goals/{id}/proposals`), reloaded on each new
 * `proposal.ready` (`readyKey`: the id of the last event of this type).
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
