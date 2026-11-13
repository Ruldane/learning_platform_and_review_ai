import { useQuery } from "@tanstack/react-query";
import { fetchLessonTitle } from "../api";
import { studyKeys } from "../queryKeys";

/** Le titre de la leçon choisie pour la session (`null` : pas de leçon choisie, rien n'est lu). */
export function useLessonTitle(lessonId: string | null) {
  return useQuery({
    queryKey: studyKeys.lesson(lessonId ?? ""),
    queryFn: ({ signal }) => fetchLessonTitle(lessonId ?? "", signal),
    enabled: lessonId !== null,
  });
}
