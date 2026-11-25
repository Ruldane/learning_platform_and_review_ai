import type { LibraryFilterValue } from "./types";

/** TanStack Query keys of the feature: identifiers and filters, never a title. */
export const lessonsKeys = {
  all: ["lessons"],
  programs: ["lessons", "programs"],
  lesson: (lessonId: string) => ["lessons", "lesson", lessonId] as const,
  ofProgram: (programId: string) => ["lessons", "of-program", programId] as const,
  resources: (filters: LibraryFilterValue) => ["lessons", "resources", filters] as const,
} as const;
