import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
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

/** `POST /goals` : enregistre l'objectif et lance le Conseil (D87). */
export async function createGoal(input: GoalInput) {
  return unwrap(
    await api.POST("/goals", {
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
 * `POST /goals/{id}/council` : relance depuis le début un Conseil dont la dernière session a
 * échoué (409 `council_not_failed` sinon, `goal_already_chosen` si un programme est lancé).
 */
export async function retryCouncil(goalId: string) {
  return unwrap(await api.POST("/goals/{goal_id}/council", goalPath(goalId)));
}

/** `GET /goals/{id}/proposals` : le dernier lot (vide après une relance, jusqu'au premier lot). */
export async function fetchProposals(goalId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/goals/{goal_id}/proposals", { ...goalPath(goalId), signal }));
}

/**
 * `GET /goals/{id}/boards` : tous les états du tableau, dans l'ordre de création, ceux des Conseils
 * précédents compris (à filtrer par `session_id`).
 */
export async function fetchBoards(goalId: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/goals/{goal_id}/boards", { ...goalPath(goalId), signal }));
}

/** `POST /proposals/{id}/choose` : un parcours, ou un mélange avec `mixWith` (D87). */
export async function chooseProposal(proposalId: string, mixWith: string | null) {
  return unwrap(
    await api.POST("/proposals/{proposal_id}/choose", {
      params: { path: { proposal_id: proposalId } },
      body: { mix_with: mixWith },
    }),
  );
}

/** `POST /boards/{id}/edits` : les retouches de January, enregistrées et renvoyées aux agents. */
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

/** Nombre de tours du débat voulu par January (`GET /settings`, de 1 à 5). */
export async function fetchDebateRounds(signal?: AbortSignal): Promise<number> {
  return unwrap(await api.GET("/settings", { signal })).debate_rounds;
}
