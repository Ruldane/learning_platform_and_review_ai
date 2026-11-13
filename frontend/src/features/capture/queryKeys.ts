import type { JournalKind } from "./types";

/** Clés TanStack Query de la feature : des identifiants et le filtre, jamais le texte capturé. */
export const captureKeys = {
  journals: ["capture", "journal"] as const,
  journal: (kind: JournalKind | null) => ["capture", "journal", kind ?? "all"] as const,
} as const;
