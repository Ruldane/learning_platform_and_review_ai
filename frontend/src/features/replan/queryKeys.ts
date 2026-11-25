/** TanStack Query keys for the feature: identifiers only, never a message or a summary. */
export const replanKeys = {
  versions: (programId: string) => ["replan", "versions", programId] as const,
  waiting: (programId: string) => ["replan", "waiting", programId] as const,
  /** The program key (`program` feature): re-read at the end of a replan; the only coupling. */
  programDetail: (programId: string) => ["program", "detail", programId] as const,
} as const;
