/** Clés TanStack Query de la feature : des identifiants seulement, jamais un titre ni une saisie. */
export const programKeys = {
  list: ["program", "list"],
  detail: (programId: string) => ["program", "detail", programId] as const,
  waitingReplan: (programId: string) => ["program", "waiting-replan", programId] as const,
  sessions: ["program", "session"],
  session: (sessionId: string) => ["program", "session", sessionId] as const,
} as const;
