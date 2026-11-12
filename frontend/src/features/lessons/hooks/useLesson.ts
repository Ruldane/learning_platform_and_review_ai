import { useQuery } from "@tanstack/react-query";
import { fetchLesson } from "../api";
import { lessonsKeys } from "../queryKeys";
import type { LessonStatus } from "../types";

const GENERATING_MS = 5000;
const WAITING_MS = 15_000;

/**
 * Quand relire une leçon : toutes les 5 s pendant qu'elle s'écrit, toutes les 15 s tant qu'elle
 * attend son tour ou sa nouvelle tentative (elle peut y rester longtemps) ; plus une fois prête.
 */
export function lessonRefetchInterval(status: LessonStatus | undefined): number | false {
  if (status === undefined || status === "ready") return false;
  return status === "generating" ? GENERATING_MS : WAITING_MS;
}

/** Une leçon (`GET /lessons/{id}`), relue d'elle-même tant qu'elle n'est pas prête. */
export function useLesson(lessonId: string) {
  return useQuery({
    queryKey: lessonsKeys.lesson(lessonId),
    queryFn: ({ signal }) => fetchLesson(lessonId, signal),
    refetchInterval: (query) => lessonRefetchInterval(query.state.data?.status),
  });
}
