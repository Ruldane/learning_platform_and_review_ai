import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import { listSessions } from "@/shared/realtime/sessionApi";
import type { ReplanRequest } from "./types";

const programPath = (programId: string) => ({ params: { path: { program_id: programId } } });

/**
 * `POST /programs/{id}/replan` (202) : lance la replanification, jamais `POST /sessions` (409
 * `graph_has_route`). 409 `replan_open` (`details.session_id`), 409 `program_not_validated`.
 */
export async function startReplan(programId: string, body: ReplanRequest) {
  return unwrap(
    await api.POST("/programs/{program_id}/replan", { ...programPath(programId), body }),
  );
}

/** `GET /programs/{id}/versions` : l'historique du plan, la plus récente d'abord. */
export async function fetchVersions(programId: string, signal?: AbortSignal) {
  return unwrap(
    await api.GET("/programs/{program_id}/versions", { ...programPath(programId), signal }),
  );
}

/**
 * La replanification de ce programme qui attend une réponse (`GET /sessions?graph=replan&
 * status=waiting_user`, sujet = programme), ou `null`.
 */
export async function fetchWaitingReplan(
  programId: string,
  signal?: AbortSignal,
): Promise<string | null> {
  const sessions = await listSessions("replan", "waiting_user", signal);
  const mine = sessions.find(
    (session) => session.subject_type === "program" && session.subject_id === programId,
  );
  return mine?.id ?? null;
}
