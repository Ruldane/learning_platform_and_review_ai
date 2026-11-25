/** TanStack Query keys of the feature: identifiers only, never a name, text or link. */
export const cvKeys = {
  profile: ["cv", "profile"],
  profileVersions: ["cv", "profile", "versions"],
  templates: ["cv", "templates"],
  /** Under the list prefix, invalidating `templates` also re-reads each detail (active one). */
  template: (templateId: string) => ["cv", "templates", templateId] as const,
  documents: ["cv", "documents"],
  review: (reviewId: string) => ["cv", "review", reviewId] as const,
  versions: ["cv", "versions"],
  version: (versionId: string) => ["cv", "version", versionId] as const,
  postings: ["cv", "postings"],
} as const;
