import type { LibraryFilterValue } from "./types";

/** Clés TanStack Query de la feature : des identifiants et des filtres, jamais un titre. */
export const lessonsKeys = {
  all: ["lessons"],
  programs: ["lessons", "programs"],
  lesson: (lessonId: string) => ["lessons", "lesson", lessonId] as const,
  ofProgram: (programId: string) => ["lessons", "of-program", programId] as const,
  resources: (filters: LibraryFilterValue) => ["lessons", "resources", filters] as const,
} as const;
