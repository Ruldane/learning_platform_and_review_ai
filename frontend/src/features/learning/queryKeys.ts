/** Clés TanStack Query de la feature : des identifiants seulement, jamais un texte d'objectif. */
export const learningKeys = {
  goals: ["learning", "goals"],
  goal: (goalId: string) => ["learning", "goal", goalId] as const,
  proposals: (goalId: string) => ["learning", "proposals", goalId] as const,
  boards: (goalId: string) => ["learning", "boards", goalId] as const,
  rounds: ["learning", "debate-rounds"],
} as const;
