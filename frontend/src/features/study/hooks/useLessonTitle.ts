import { useQuery } from "@tanstack/react-query";
import { fetchLessonTitle } from "../api";
import { studyKeys } from "../queryKeys";

/** The title of the lesson chosen for the session (`null`: no lesson chosen, nothing is read). */
export function useLessonTitle(lessonId: string | null) {
  return useQuery({
    queryKey: studyKeys.lesson(lessonId ?? ""),
    queryFn: ({ signal }) => fetchLessonTitle(lessonId ?? "", signal),
    enabled: lessonId !== null,
  });
}
