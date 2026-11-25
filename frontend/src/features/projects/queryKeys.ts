/** TanStack Query keys for projects: identifiers only, never a link or a description. */
export const projectKeys = {
  all: ["projects"] as const,
  list: ["projects", "list"] as const,
  one: (projectId: string) => ["projects", "one", projectId] as const,
  github: (projectId: string) => ["projects", "github", projectId] as const,
} as const;
