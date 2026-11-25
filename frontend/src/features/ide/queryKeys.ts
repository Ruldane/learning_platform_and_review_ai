/** TanStack Query keys of the IDE: all under `["ide", …]`. */
export const ideKeys = {
  exercises: ["ide", "exercises"] as const,
  sessions: ["ide", "sessions"] as const,
  session: (id: string) => ["ide", "session", id] as const,
  notebook: (id: string, path: string) => ["ide", "notebook", id, path] as const,
  notes: (sessionId: string) => ["ide", "notes", sessionId] as const,
  runs: (sessionId: string) => ["ide", "runs", sessionId] as const,
  usage: (sessionId: string) => ["ide", "usage", sessionId] as const,
  preferences: ["ide", "preferences"] as const,
} as const;
