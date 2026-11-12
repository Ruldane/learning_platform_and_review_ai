import { useQuery } from "@tanstack/react-query";
import { fetchProgramLessons } from "../api";
import { lessonsKeys } from "../queryKeys";

/** Les leçons d'un programme (`GET /programs/{id}/lessons`), dans l'ordre du programme. */
export function useProgramLessons(programId: string | undefined) {
  return useQuery({
    queryKey: lessonsKeys.ofProgram(programId ?? ""),
    queryFn: ({ signal }) => fetchProgramLessons(programId ?? "", signal),
    enabled: programId !== undefined,
  });
}
