import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";
import type { GoalInput } from "./types";

const goalPath = (goalId: string) => ({ params: { path: { goal_id: goalId } } });

/** `GET /goals`. */
export async function fetchGoals(signal?: AbortSignal) {
  return unwrap(await api.GET("/goals", { signal }));
}

/** `GET /goals/{id}`. */
export async function fetchGoal(goalId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/goals/{goal_id}", { ...goalPath(goalId), signal }));
}

/** `POST /goals`: saves the goal and starts the Council (D87). */
export async function createGoal(input: GoalInput, source?: RunSource) {
  return unwrap(
    await api.POST("/goals", {
      headers: runSourceHeaders(source),
      body: {
        text: input.text,
        target_role: input.targetRole,
        deadline: input.deadline,
        weekly_hours: input.weeklyHours,
      },
    }),
  );
}

/**
 * `POST /goals/{id}/council`: restarts from the beginning a Council whose last session has
 * failed (otherwise 409 `council_not_failed`, `goal_already_chosen` if a program is started).
 */
export async function retryCouncil(goalId: string, source?: RunSource) {
  return unwrap(
    await api.POST("/goals/{goal_id}/council", {
      ...goalPath(goalId),
      headers: runSourceHeaders(source),
    }),
  );
}

/** `GET /goals/{id}/proposals`: the latest batch (empty after a restart, until the first batch). */
export async function fetchProposals(goalId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/goals/{goal_id}/proposals", { ...goalPath(goalId), signal }));
}

/**
 * `GET /goals/{id}/boards`: all board states, in creation order, including those of earlier
 * Councils (to filter by `session_id`).
 */
export async function fetchBoards(goalId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/goals/{goal_id}/boards", { ...goalPath(goalId), signal }));
}

/** `POST /proposals/{id}/choose`: a path, or a mix with `mixWith` (D87). */
export async function chooseProposal(proposalId: string, mixWith: string | null) {
  return unwrap(
    await api.POST("/proposals/{proposal_id}/choose", {
      params: { path: { proposal_id: proposalId } },
      body: { mix_with: mixWith },
    }),
  );
}

/** `POST /boards/{id}/edits`: January's edits, saved and sent back to the agents. */
export async function postBoardEdit(
  boardId: string,
  edit: { scene: Record<string, unknown>; note: string },
) {
  return unwrap(
    await api.POST("/boards/{board_id}/edits", {
      params: { path: { board_id: boardId } },
      body: edit,
    }),
  );
}

/** Number of debate rounds January wants (`GET /settings`, from 1 to 5). */
export async function fetchDebateRounds(signal?: AbortSignal): Promise<number> {
  return unwrap(await api.GET("/settings", { signal })).debate_rounds;
}
