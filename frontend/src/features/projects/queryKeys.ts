/** Clés TanStack Query des projets : des identifiants seulement, jamais un lien ni une description. */
export const projectKeys = {
  all: ["projects"] as const,
  list: ["projects", "list"] as const,
  one: (projectId: string) => ["projects", "one", projectId] as const,
} as const;
