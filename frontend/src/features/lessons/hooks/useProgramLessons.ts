import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { fetchProgramLessons } from "../api";
import { lessonsKeys } from "../queryKeys";
import { lessonIsInProgress, lessonsRefetchInterval } from "./polling";

/**
 * The lessons of a program (`GET /programs/{id}/lessons`), in program order; re-read
 * on their own while a lesson is being written or waiting (for a bounded time, see
 * `lessonsRefetchInterval`).
 */
export function useProgramLessons(programId: string | undefined) {
  /** Read number (`dataUpdateCount`) at which a lesson was still being written. */
  const busyAt = useRef<number | null>(null);
  return useQuery({
    queryKey: lessonsKeys.ofProgram(programId ?? ""),
    queryFn: ({ signal }) => fetchProgramLessons(programId ?? "", signal),
    enabled: programId !== undefined,
    // A task ticked in the program changes a lesson's progress: re-read on opening.
    refetchOnMount: "always",
    refetchInterval: (query) => {
      const lessons = query.state.data;
      const updates = query.state.dataUpdateCount;
      if (lessons?.some(lessonIsInProgress)) busyAt.current = updates;
      else busyAt.current ??= updates;
      return lessonsRefetchInterval(lessons, updates - busyAt.current);
    },
  });
}
