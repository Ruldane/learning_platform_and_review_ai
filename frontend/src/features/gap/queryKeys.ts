/** TanStack Query keys of the feature: identifiers only, never a link or posting text. */
export const gapKeys = {
  postings: ["gap", "postings"],
  posting: (postingId: string) => ["gap", "posting", postingId] as const,
  gap: (postingId: string) => ["gap", "gap", postingId] as const,
  topMissing: ["gap", "top-missing"],
  targetPrograms: ["gap", "target-programs"],
  applicationCheck: (postingId: string) => ["gap", "application-check", postingId] as const,
  cvs: (postingId: string) => ["gap", "cvs", postingId] as const,
} as const;
