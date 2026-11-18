/** Clés TanStack Query de la feature : des identifiants seulement, jamais un lien ni un texte d'offre. */
export const gapKeys = {
  postings: ["gap", "postings"],
  posting: (postingId: string) => ["gap", "posting", postingId] as const,
  gap: (postingId: string) => ["gap", "gap", postingId] as const,
  topMissing: ["gap", "top-missing"],
  applicationCheck: (postingId: string) => ["gap", "application-check", postingId] as const,
  cvs: (postingId: string) => ["gap", "cvs", postingId] as const,
} as const;
