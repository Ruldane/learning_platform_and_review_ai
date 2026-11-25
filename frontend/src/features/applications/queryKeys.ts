/**
 * TanStack Query keys of the feature: identifiers only, never a company name, an
 * posting text or a draft. `all` is the prefix of everything: re-reading it updates everything.
 */
export const applicationsKeys = {
  all: ["applications"],
  list: ["applications", "list"],
  stats: ["applications", "stats"],
  one: (applicationId: string) => ["applications", "one", applicationId] as const,
  reminders: ["applications", "reminders"],
  kit: (applicationId: string) => ["applications", "kit", applicationId] as const,
  /** All interviews (the list prefix). */
  allInterviews: ["applications", "interviews"],
  /** The interviews of a record, or (`null`) those without a record. */
  interviews: (applicationId: string | null) =>
    ["applications", "interviews", applicationId ?? "free"] as const,
  interview: (interviewId: string) => ["applications", "interview", interviewId] as const,
  postings: ["applications", "postings"],
  /** The committee runs of a posting (the prefix of the committee reads). */
  committees: (postingId: string) => ["applications", "committees", postingId] as const,
  committee: (runId: string) => ["applications", "committee", runId] as const,
  /** The CV versions of a posting. */
  cvVersions: (postingId: string) => ["applications", "cv-versions", postingId] as const,
} as const;
