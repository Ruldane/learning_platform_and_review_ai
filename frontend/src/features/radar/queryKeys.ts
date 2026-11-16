/** Clés TanStack Query du radar : des identifiants seulement, jamais un poste, une zone ni une offre. */
export const radarKeys = {
  all: ["radar"] as const,
  latest: ["radar", "latest"] as const,
  history: ["radar", "history"] as const,
  run: (runId: string) => ["radar", "run", runId] as const,
  /** La session qui fait tourner un relevé (retrouvée quand le serveur ne la donne pas). */
  session: (runId: string) => ["radar", "session", runId] as const,
} as const;
