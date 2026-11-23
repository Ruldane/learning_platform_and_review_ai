import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components, paths } from "@/shared/api/schema";
import { RUN_HEADER, type RunSource } from "@/shared/lib/runSource";
import type { ConversationMessage } from "./api";

export type TrainingSession = components["schemas"]["TrainingSessionOut"];
export type TrainingStart = components["schemas"]["TrainingStart"];
export type TrainingMode = TrainingSession["mode"];
export type TrainingChange =
  paths["/api/v1/study-sessions/training/{study_session_id}"]["patch"]["requestBody"]["content"]["application/json"];

const ref = (id: string) => ({ path: { study_session_id: id } });

export async function fetchTraining(id: string | undefined, signal?: AbortSignal) {
  return id === undefined
    ? unwrap(await api.GET("/study-sessions/training/open", { signal }))
    : unwrap(
        await api.GET("/study-sessions/training/{study_session_id}", { params: ref(id), signal }),
      );
}

export async function startTraining(body: TrainingStart) {
  return unwrap(await api.POST("/study-sessions/training", { body }));
}

export async function changeTraining(id: string, body: TrainingChange) {
  return unwrap(
    await api.PATCH("/study-sessions/training/{study_session_id}", { params: ref(id), body }),
  );
}

export async function sendTrainingQuestion(
  id: string,
  message: ConversationMessage,
  source: RunSource,
) {
  return unwrap(
    await api.POST("/study-sessions/training/{study_session_id}/messages", {
      params: ref(id),
      headers: { [RUN_HEADER]: source },
      body: { request_id: message.request_id, question: message.question, strong: message.strong },
    }),
  );
}

export async function listTrainingLessons(signal?: AbortSignal) {
  const programs = unwrap(await api.GET("/programs", { signal }));
  const catalogue = await Promise.all(
    programs.map(async ({ id }) =>
      unwrap(
        await api.GET("/programs/{program_id}/lessons", {
          params: { path: { program_id: id } },
          signal,
        }),
      ),
    ),
  );
  return catalogue.flat().filter(({ status }) => status === "ready");
}
