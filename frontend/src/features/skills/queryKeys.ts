/** TanStack Query keys of the feature: identifiers and numbers, never a skill name. */
export const skillKeys = {
  graph: ["skills", "graph"],
  detail: (skillId: string) => ["skills", "detail", skillId] as const,
  history: (weeks: number) => ["skills", "history", weeks] as const,
  compare: (postingId: string | null) => ["skills", "compare", postingId ?? "goal"] as const,
  postings: ["skills", "postings"],
} as const;
