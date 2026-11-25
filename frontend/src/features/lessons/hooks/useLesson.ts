import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { fetchLesson } from "../api";
import { lessonsKeys } from "../queryKeys";
import { lessonIsInProgress, lessonRefetchInterval } from "./polling";

/**
 * A lesson (`GET /lessons/{id}`), re-read on its own while it is not ready, then while
 * its PDF has not arrived (for a bounded time, see `lessonRefetchInterval`).
 */
export function useLesson(lessonId: string) {
  /** Read number (`dataUpdateCount`) at which the lesson was first seen ready. */
  const readyAt = useRef<number | null>(null);
  return useQuery({
    queryKey: lessonsKeys.lesson(lessonId),
    queryFn: ({ signal }) => fetchLesson(lessonId, signal),
    refetchInterval: (query) => {
      const lesson = query.state.data;
      const updates = query.state.dataUpdateCount;
      if (lesson?.status !== "ready" || lessonIsInProgress(lesson)) readyAt.current = null;
      else readyAt.current ??= updates;
      return lessonRefetchInterval(lesson, updates - (readyAt.current ?? updates));
    },
  });
}
