import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { studySessionPath } from "@/shared/lib/studyRoutes";
import {
  changeTraining,
  fetchTraining,
  startTraining,
  type TrainingChange,
  type TrainingSession,
} from "../trainingApi";
import { following } from "./useConversation";

const key = (id?: string) => ["conversations", "training", id ?? "open"] as const;
export const trainingPath = (id: string) => studySessionPath(id, "training");

export function useTraining(studyId?: string) {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const query = useQuery({
    queryKey: key(studyId),
    queryFn: ({ signal }) => fetchTraining(studyId, signal),
    refetchInterval: ({ state }) =>
      state.data?.status === "open" && following(state.data.conversation.turns, submitted)
        ? 2000
        : false,
  });
  const update = (session: TrainingSession) => {
    client.setQueryData(key(session.id), session);
    client.setQueryData(key(), session.status === "open" ? session : null);
  };
  const launch = useMutation({
    mutationFn: startTraining,
    onSuccess: (session) => {
      setSubmitted(null);
      update(session);
      void navigate(trainingPath(session.id));
    },
  });
  const change = useMutation({
    mutationFn: (body: TrainingChange) => changeTraining(studyId ?? "", body),
    onSuccess: (session) => {
      update(session);
      if (session.status !== "open") void client.invalidateQueries({ queryKey: ["study"] });
    },
  });
  const sessionId = following(query.data?.conversation.turns, submitted);
  const refresh = () => void query.refetch();
  return {
    query,
    launch,
    change,
    sessionId,
    refresh,
    submitted: (id: string) => {
      setSubmitted(id);
      refresh();
    },
  };
}
