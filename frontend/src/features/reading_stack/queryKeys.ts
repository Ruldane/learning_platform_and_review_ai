export const readingKeys = {
  items: ["reading-stack", "items"] as const,
  detail: (id: string) => ["reading-stack", "entry", id] as const,
  sources: ["reading-stack", "sources"] as const,
  programs: ["reading-stack", "programs"] as const,
};
