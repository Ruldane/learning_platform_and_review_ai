import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { fetchLesson } from "../api";
import { lessonsKeys } from "../queryKeys";
import { lessonRefetchInterval } from "./polling";

/**
 * Une leçon (`GET /lessons/{id}`), relue d'elle-même tant qu'elle n'est pas prête, puis tant que
 * son PDF n'est pas arrivé (pour un temps borné, voir `lessonRefetchInterval`).
 */
export function useLesson(lessonId: string) {
  /** Numéro de lecture (`dataUpdateCount`) où la leçon a été vue prête pour la première fois. */
  const readyAt = useRef<number | null>(null);
  return useQuery({
    queryKey: lessonsKeys.lesson(lessonId),
    queryFn: ({ signal }) => fetchLesson(lessonId, signal),
    refetchInterval: (query) => {
      const lesson = query.state.data;
      const updates = query.state.dataUpdateCount;
      if (lesson?.status !== "ready") readyAt.current = null;
      else readyAt.current ??= updates;
      return lessonRefetchInterval(lesson, updates - (readyAt.current ?? updates));
    },
  });
}
