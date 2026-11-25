import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

/** `GET /skills/graph`: skills, prerequisites and scores per domain (not cached server-side). */
export async function fetchSkillGraph(signal?: AbortSignal) {
  return unwrap(await api.GET("/skills/graph", { signal }));
}

/** `GET /skills/{id}`: evidence, offers and next action; 404 `skill_not_found`. */
export async function fetchSkillDetail(skillId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/skills/{skill_id}", { params: { path: { skill_id: skillId } }, signal }),
  );
}

/** `GET /skills/history?weeks=`: one reading per week; the last one is the current week. */
export async function fetchSkillHistory(weeks: number, signal?: AbortSignal) {
  return unwrap(await api.GET("/skills/history", { params: { query: { weeks } }, signal }));
}

/** The target of a comparison: the target role (goal) or an analyzed offer. */
export type CompareTarget = { kind: "goal" } | { kind: "posting"; postingId: string };

/**
 * `GET /skills/compare`: without `goal_id`, the most recent goal that has a program (404
 * `no_compare_target` when there is none). With an offer: its learnable skills;
 * 404 `no_compare_target` until its gap is filed, 404 `posting_not_found`.
 */
export async function fetchSkillCompare(target: CompareTarget, signal?: AbortSignal) {
  const query =
    target.kind === "goal"
      ? { target: "goal" as const }
      : { target: "posting" as const, posting_id: target.postingId };
  return unwrap(await api.GET("/skills/compare", { params: { query }, signal }));
}

/** `GET /postings`: the offers, to choose the one to compare against. */
export async function fetchPostingChoices(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}
