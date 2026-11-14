import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

/** `GET /skills/graph` : compétences, prérequis et scores par domaine (jamais en cache côté serveur). */
export async function fetchSkillGraph(signal?: AbortSignal) {
  return unwrap(await api.GET("/skills/graph", { signal }));
}

/** `GET /skills/{id}` : preuves, offres et prochaine action ; 404 `skill_not_found`. */
export async function fetchSkillDetail(skillId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/skills/{skill_id}", { params: { path: { skill_id: skillId } }, signal }),
  );
}

/** `GET /skills/history?weeks=` : un relevé par semaine, le dernier est la semaine en cours. */
export async function fetchSkillHistory(weeks: number, signal?: AbortSignal) {
  return unwrap(await api.GET("/skills/history", { params: { query: { weeks } }, signal }));
}

/** La cible d'une comparaison : le poste cible (objectif) ou une offre analysée. */
export type CompareTarget = { kind: "goal" } | { kind: "posting"; postingId: string };

/**
 * `GET /skills/compare` : sans `goal_id`, l'objectif le plus récent qui a un programme (404
 * `no_compare_target` quand il n'y en a aucun). Avec une offre : ses compétences apprenables ;
 * 404 `no_compare_target` tant que son écart n'est pas rangé, 404 `posting_not_found`.
 */
export async function fetchSkillCompare(target: CompareTarget, signal?: AbortSignal) {
  const query =
    target.kind === "goal"
      ? { target: "goal" as const }
      : { target: "posting" as const, posting_id: target.postingId };
  return unwrap(await api.GET("/skills/compare", { params: { query }, signal }));
}

/** `GET /postings` : les offres, pour choisir celle à laquelle se comparer. */
export async function fetchPostingChoices(signal?: AbortSignal) {
  return unwrap(await api.GET("/postings", { signal }));
}
