import { useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { debateDetails, listDebates, startDebate, storeJudgment } from "../api";

const recent = ["expert_debates", "recent"] as const;
const details = (id: string) => ["expert_debates", id] as const;
export const debatePath = (id: string) => `/study/debates/${encodeURIComponent(id)}`;

export function useDebates(id: string) {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const attempt = useRef<{ id: string; question: string } | null>(null);
  const list = useQuery({ queryKey: recent, queryFn: ({ signal }) => listDebates(signal) });
  const detail = useQuery({
    queryKey: details(id),
    enabled: Boolean(id),
    queryFn: ({ signal }) => debateDetails(id, signal),
    refetchInterval: ({ state }) => {
      const current = state.data?.status;
      return current === "running" || current === "waiting_user" || current === "paused"
        ? 900
        : false;
    },
  });
  const start = useMutation({
    mutationFn: (question: string) => {
      if (attempt.current?.question !== question)
        attempt.current = { id: crypto.randomUUID(), question };
      return startDebate(attempt.current.id, question);
    },
    onSuccess: async ({ debate_id }) => {
      attempt.current = null;
      await navigate(debatePath(debate_id));
      await cache.invalidateQueries({ queryKey: recent });
    },
  });
  const judgment = useMutation({
    mutationFn: (text: string) => storeJudgment(id, text),
    onSuccess: (saved) => {
      cache.setQueryData(details(id), saved);
    },
  });
  return { list, detail, start, judgment };
}
