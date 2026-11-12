import { t } from "@/shared/i18n/t";
import type { BoardStateView } from "@/shared/session-ui";
import type { BoardOut, GoalOut, GoalRow, ProposalOut, ProposalView } from "./types";

export function toGoalRow(goal: GoalOut): GoalRow {
  return {
    id: goal.id,
    text: goal.text,
    targetRole: goal.target_role,
    deadline: goal.deadline,
    weeklyHours: goal.weekly_hours,
    status: goal.status,
    programId: goal.program_id,
  };
}

/** Les objectifs du plus récent au plus ancien. */
export function newestFirst(goals: GoalOut[]): GoalOut[] {
  return [...goals].sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export function toProposalView(proposal: ProposalOut): ProposalView {
  return {
    id: proposal.id,
    rank: proposal.rank,
    name: proposal.name,
    promise: proposal.promise,
    durationWeeks: proposal.duration_weeks,
    weeklyHours: proposal.weekly_hours,
    skills: proposal.skills,
    finalProject: proposal.final_project,
    tradeoffs: proposal.tradeoffs,
    boardId: proposal.board_id,
    chosen: proposal.chosen,
  };
}

export function toBoardView(board: BoardOut): BoardStateView {
  return {
    id: board.id,
    kind: board.kind,
    title: board.title !== "" ? board.title : t(`session.board.kinds.${board.kind}`),
    step: board.step,
    mermaid: board.mermaid,
    scene: board.scene,
    author: board.author,
    createdAt: board.created_at,
  };
}
