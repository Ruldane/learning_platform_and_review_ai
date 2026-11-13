/** Clés TanStack Query de la feature : des identifiants et des nombres, jamais un nom de compétence. */
export const skillKeys = {
  graph: ["skills", "graph"],
  detail: (skillId: string) => ["skills", "detail", skillId] as const,
  history: (weeks: number) => ["skills", "history", weeks] as const,
  compare: ["skills", "compare"],
} as const;
