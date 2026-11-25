/** TanStack Query keys of the feature: identifiers only, never a title or an answer. */
export const studyKeys = {
  summary: ["study", "summary"],
  session: (studyId: string) => ["study", "session", studyId] as const,
  lesson: (lessonId: string) => ["study", "lesson", lessonId] as const,
} as const;
