/** Clés TanStack Query de la feature : des identifiants seulement, jamais un titre ni une réponse. */
export const studyKeys = {
  summary: ["study", "summary"],
  session: (studyId: string) => ["study", "session", studyId] as const,
  lesson: (lessonId: string) => ["study", "lesson", lessonId] as const,
} as const;
