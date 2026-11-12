import { http, HttpResponse } from "msw";
import { apiBaseUrl } from "@/shared/api/client";

export const API = `${apiBaseUrl}/api/v1`;

/** Un objectif tel que le back le rend (`GoalOut`). */
export const goalOut = (over: Record<string, unknown> = {}) => ({
  id: "g1",
  text: "Devenir ingénieure data",
  target_role: "Data engineer",
  deadline: null,
  weekly_hours: 8,
  status: "council",
  council_session_id: "c1",
  program_id: null,
  program_session_id: null,
  created_at: "2026-11-12T10:00:00Z",
  ...over,
});

/** Un statut de session (`SessionView`). */
export const sessionOut = (id: string, status: string, over: Record<string, unknown> = {}) => ({
  id,
  graph: "learning_council",
  status,
  subject_type: "goal",
  subject_id: "g1",
  last_seq: 0,
  pending_interrupt: null,
  error: null,
  cost_usd: 0,
  tokens_in: 0,
  tokens_out: 0,
  created_at: "2026-11-12T10:00:00Z",
  updated_at: "2026-11-12T10:00:00Z",
  ...over,
});

export const proposalOut = (id: string, rank: number, over: Record<string, unknown> = {}) => ({
  id,
  goal_id: "g1",
  batch: 1,
  rank,
  name: `Parcours ${rank}`,
  promise: "Une promesse.",
  duration_weeks: 8,
  weekly_hours: 6,
  skills: ["Python"],
  final_project: "Un projet",
  tradeoffs: ["Un compromis"],
  board_id: null,
  chosen: false,
  ...over,
});

export const boardOut = (id: string, over: Record<string, unknown> = {}) => ({
  id,
  goal_id: "g1",
  session_id: "c1",
  parent_id: null,
  kind: "domain_map",
  title: "Carte du domaine",
  step: 1,
  mermaid: "flowchart TD\n  A --> B",
  scene: null,
  author: "scribe",
  created_at: "2026-11-12T10:00:00Z",
  ...over,
});

interface CouncilApi {
  goal?: Record<string, unknown>;
  status?: string;
  proposals?: Record<string, unknown>[];
  boards?: Record<string, unknown>[];
  rounds?: number;
  /** Remplace la réponse de `GET /goals/g1` (une erreur, une réponse qui change d'une lecture à l'autre). */
  goalReply?: () => Response;
}

/**
 * Les lectures REST d'une page du Conseil : l'objectif, son statut, ses propositions, ses tableaux
 * et les réglages. `proposals` et `boards` sont lus à chaque requête : un test peut les changer.
 */
export function councilApi(api: CouncilApi = {}) {
  const state = {
    goal: api.goal ?? goalOut(),
    status: api.status ?? "running",
    proposals: api.proposals ?? [],
    boards: api.boards ?? [],
  };
  const handlers = [
    http.get(`${API}/goals/g1`, () => api.goalReply?.() ?? HttpResponse.json(state.goal)),
    http.get(`${API}/goals/g1/proposals`, () => HttpResponse.json(state.proposals)),
    http.get(`${API}/goals/g1/boards`, () => HttpResponse.json(state.boards)),
    http.get(`${API}/sessions/c1`, () => HttpResponse.json(sessionOut("c1", state.status))),
    http.get(`${API}/settings`, () => HttpResponse.json({ debate_rounds: api.rounds ?? 3 })),
  ];
  return { state, handlers };
}
