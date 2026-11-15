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
} as const;
