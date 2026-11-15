/**
 * Clés TanStack Query de la feature : des identifiants seulement, jamais un nom d'entreprise, un
 * texte d'offre ni un brouillon. `all` est le préfixe de tout : le relire met tout à jour.
 */
export const applicationsKeys = {
  all: ["applications"],
  list: ["applications", "list"],
  stats: ["applications", "stats"],
  one: (applicationId: string) => ["applications", "one", applicationId] as const,
  reminders: ["applications", "reminders"],
  kit: (applicationId: string) => ["applications", "kit", applicationId] as const,
  /** Tous les entretiens (le préfixe des listes). */
  allInterviews: ["applications", "interviews"],
  /** Les entretiens d'une fiche, ou (`null`) ceux sans fiche. */
  interviews: (applicationId: string | null) =>
    ["applications", "interviews", applicationId ?? "free"] as const,
  interview: (interviewId: string) => ["applications", "interview", interviewId] as const,
  postings: ["applications", "postings"],
} as const;
