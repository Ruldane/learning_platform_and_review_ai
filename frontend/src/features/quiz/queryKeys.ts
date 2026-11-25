/** TanStack Query keys for the feature: identifiers only, never a prompt or an answer. */
export const quizKeys = {
  programs: ["quiz", "programs"],
  list: (programId: string) => ["quiz", "list", programId] as const,
  quiz: (quizId: string) => ["quiz", "quiz", quizId] as const,
  attempt: (quizId: string, attemptId: string) => ["quiz", "attempt", quizId, attemptId] as const,
  due: ["quiz", "due-cards"],
} as const;
