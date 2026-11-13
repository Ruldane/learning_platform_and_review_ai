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

/**
 * `GET /skills/compare?target=goal` : sans `goal_id`, l'objectif le plus récent qui a un
 * programme. 404 `no_compare_target` quand il n'y en a aucun.
 */
export async function fetchSkillCompare(signal?: AbortSignal) {
  return unwrap(
    await api.GET("/skills/compare", { params: { query: { target: "goal" } }, signal }),
  );
}
