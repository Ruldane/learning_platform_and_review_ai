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
import { listKey, threadKey } from "./useConversationList";

const key = (id?: string) => threadKey("training", id);
export function trainingPath(id: string, skillId = "") {
  const path = studySessionPath(id, "training");
  return skillId ? `${path}?${new URLSearchParams({ skill: skillId })}` : path;
}

export function newTrainingPath(skillId = "") {
  const params = new URLSearchParams({ new: "1" });
  if (skillId) params.set("skill", skillId);
  return `/study/training?${params}`;
}

function useTrainingQuery(studyId: string | undefined, fresh: boolean, submitted: string | null) {
  return useQuery({
    queryKey: key(studyId),
    queryFn: ({ signal }) => fetchTraining(studyId, signal),
    enabled: !fresh,
    refetchInterval: ({ state }) =>
      following(state.data?.conversation.turns, submitted) ? 2000 : false,
  });
}

export function useTraining(studyId?: string, skillId = "", fresh = false) {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [submitted, setSubmitted] = useState<string | null>(null);
  const query = useTrainingQuery(studyId, fresh, submitted);
  const update = (session: TrainingSession) => {
    client.setQueryData(key(session.id), session);
    void client.invalidateQueries({ queryKey: listKey("training") });
  };
  const launch = useMutation({
    mutationFn: startTraining,
    onSuccess: (session) => {
      setSubmitted(null);
      update(session);
      void client.invalidateQueries({ queryKey: key() });
      void navigate(trainingPath(session.id, skillId));
    },
  });
  const change = useMutation({
    mutationFn: (body: TrainingChange) => changeTraining(studyId ?? "", body),
    onSuccess: (session) => {
      update(session);
      if (session.status !== "open") {
        void client.invalidateQueries({ queryKey: ["study"] });
        void client.invalidateQueries({ queryKey: key() });
      }
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
      void client.invalidateQueries({ queryKey: listKey("training") });
      refresh();
    },
  };
}
