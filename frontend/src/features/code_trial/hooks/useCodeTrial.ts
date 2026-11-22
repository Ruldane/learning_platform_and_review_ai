import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { openTrial, readTrial, saveVerdict } from "../api";
import type { TrialVerdict } from "../types";

const trials = (sessionId: string) => ["code_trial", sessionId] as const;

export function useCodeTrial(sessionId: string, trialId?: string) {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const key = [...trials(sessionId), trialId ?? "latest"];
  const trial = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => readTrial(sessionId, trialId, signal),
    staleTime: 0,
    refetchInterval: ({ state }) => (state.data?.status === "running" ? 700 : false),
  });
  const open = useMutation({
    mutationFn: () => openTrial(sessionId),
    async onSuccess(result) {
      await cache.invalidateQueries({ queryKey: trials(sessionId) });
      await navigate(
        `/code/${encodeURIComponent(sessionId)}/proces/${encodeURIComponent(result.trial_id)}`,
        {
          replace: !!trialId,
        },
      );
    },
  });
  const decide = useMutation({
    mutationFn: ({ id, verdict }: { id: string; verdict: TrialVerdict }) =>
      saveVerdict(sessionId, id, verdict),
    async onSuccess(saved) {
      cache.setQueryData(key, saved);
      await cache.invalidateQueries({ queryKey: trials(sessionId) });
    },
  });
  return { trial, open, decide };
}
