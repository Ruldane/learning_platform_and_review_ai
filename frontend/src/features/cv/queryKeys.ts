/** Clés TanStack Query de la feature : des identifiants seulement, jamais un nom, un texte ni un lien. */
export const cvKeys = {
  profile: ["cv", "profile"],
  profileVersions: ["cv", "profile", "versions"],
  templates: ["cv", "templates"],
  /** Sous le préfixe de la liste : invalider `templates` relit aussi chaque détail (modèle actif). */
  template: (templateId: string) => ["cv", "templates", templateId] as const,
  documents: ["cv", "documents"],
  review: (reviewId: string) => ["cv", "review", reviewId] as const,
  versions: ["cv", "versions"],
  version: (versionId: string) => ["cv", "version", versionId] as const,
  postings: ["cv", "postings"],
} as const;
