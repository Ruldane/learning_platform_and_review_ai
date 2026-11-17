/** Clés TanStack Query de l'IDE : toutes sous `["ide", …]`. */
export const ideKeys = {
  exercises: ["ide", "exercises"] as const,
  sessions: ["ide", "sessions"] as const,
  session: (id: string) => ["ide", "session", id] as const,
  notes: (sessionId: string) => ["ide", "notes", sessionId] as const,
  usage: (sessionId: string) => ["ide", "usage", sessionId] as const,
  preferences: ["ide", "preferences"] as const,
} as const;
