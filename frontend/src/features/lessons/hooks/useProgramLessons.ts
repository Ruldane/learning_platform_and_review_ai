import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { fetchProgramLessons } from "../api";
import { lessonsKeys } from "../queryKeys";
import { lessonIsInProgress, lessonsRefetchInterval } from "./polling";

/**
 * Les leçons d'un programme (`GET /programs/{id}/lessons`), dans l'ordre du programme ; relues
 * d'elles-mêmes tant qu'une leçon s'écrit ou attend (pour un temps borné, voir
 * `lessonsRefetchInterval`).
 */
export function useProgramLessons(programId: string | undefined) {
  /** Numéro de lecture (`dataUpdateCount`) où une leçon s'écrivait encore. */
  const busyAt = useRef<number | null>(null);
  return useQuery({
    queryKey: lessonsKeys.ofProgram(programId ?? ""),
    queryFn: ({ signal }) => fetchProgramLessons(programId ?? "", signal),
    enabled: programId !== undefined,
    // Une tâche cochée dans le programme change l'avancement d'une leçon : relire à l'ouverture.
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
