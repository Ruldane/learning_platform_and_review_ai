import type { JournalKind } from "./types";

/** TanStack Query keys of the feature: ids and the filter, never the captured text. */
export const captureKeys = {
  journals: ["capture", "journal"] as const,
  journal: (kind: JournalKind | null) => ["capture", "journal", kind ?? "all"] as const,
} as const;
