/** Clés TanStack Query de la feature : des identifiants seulement, jamais un énoncé ni une réponse. */
export const quizKeys = {
  programs: ["quiz", "programs"],
  list: (programId: string) => ["quiz", "list", programId] as const,
  quiz: (quizId: string) => ["quiz", "quiz", quizId] as const,
  attempt: (quizId: string, attemptId: string) => ["quiz", "attempt", quizId, attemptId] as const,
  due: ["quiz", "due-cards"],
} as const;
