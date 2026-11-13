/** Clés TanStack Query de la feature : des identifiants seulement, jamais un message ni un bilan. */
export const replanKeys = {
  versions: (programId: string) => ["replan", "versions", programId] as const,
  waiting: (programId: string) => ["replan", "waiting", programId] as const,
  /** Clé du programme (feature `program`) : relu à la fin d'une replanification, seul couplage. */
  programDetail: (programId: string) => ["program", "detail", programId] as const,
} as const;
