/** TanStack Query keys of the feature: identifiers only, never goal text. */
export const learningKeys = {
  goals: ["learning", "goals"],
  goal: (goalId: string) => ["learning", "goal", goalId] as const,
  proposals: (goalId: string) => ["learning", "proposals", goalId] as const,
  boards: (goalId: string) => ["learning", "boards", goalId] as const,
  rounds: ["learning", "debate-rounds"],
} as const;
