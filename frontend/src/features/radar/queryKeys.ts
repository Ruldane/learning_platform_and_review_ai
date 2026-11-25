/** TanStack Query keys for the radar: identifiers only, never a role, area or offer. */
export const radarKeys = {
  all: ["radar"] as const,
  latest: ["radar", "latest"] as const,
  history: ["radar", "history"] as const,
  run: (runId: string) => ["radar", "run", runId] as const,
  /** The session running a sweep (found again when the server does not give it). */
  session: (runId: string) => ["radar", "session", runId] as const,
} as const;
