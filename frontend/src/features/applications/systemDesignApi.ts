import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { BoardEdit } from "@/shared/session-ui";

export type Design = components["schemas"]["DesignState"];
export type DesignReview = components["schemas"]["SystemDesignReview"];

export async function readDesign(interviewId: string | undefined, signal: AbortSignal) {
  if (interviewId) {
    return unwrap(
      await api.GET("/interviews/{interview_id}/design", {
        params: { path: { interview_id: interviewId } },
        signal,
      }),
    );
  }
  return unwrap(await api.GET("/system-design", { signal }));
}

export async function startDesign(source: RunSource) {
  return unwrap(
    await api.POST("/interviews", {
      headers: runSourceHeaders(source),
      body: { mode: "case", duration_min: 30, language: "fr", system_design: true },
    }),
  );
}

export async function saveDesignBoard(boardId: string, edit: BoardEdit) {
  return unwrap(
    await api.POST("/boards/{board_id}/edits", {
      params: { path: { board_id: boardId } },
      body: edit,
    }),
  );
}
