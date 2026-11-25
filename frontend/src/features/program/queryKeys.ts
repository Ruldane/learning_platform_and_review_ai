/** TanStack Query keys of the feature: identifiers only, never a title or input. */
export const programKeys = {
  list: ["program", "list"],
  detail: (programId: string) => ["program", "detail", programId] as const,
  waitingReplan: (programId: string) => ["program", "waiting-replan", programId] as const,
  sessions: ["program", "session"],
  session: (sessionId: string) => ["program", "session", sessionId] as const,
} as const;
