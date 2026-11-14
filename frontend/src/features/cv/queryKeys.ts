/** Clés TanStack Query de la feature : des identifiants seulement, jamais un nom, un texte ni un lien. */
export const cvKeys = {
  profile: ["cv", "profile"],
  profileVersions: ["cv", "profile", "versions"],
  templates: ["cv", "templates"],
  template: (templateId: string) => ["cv", "template", templateId] as const,
  documents: ["cv", "documents"],
  review: (reviewId: string) => ["cv", "review", reviewId] as const,
  versions: ["cv", "versions"],
  version: (versionId: string) => ["cv", "version", versionId] as const,
  postings: ["cv", "postings"],
} as const;
