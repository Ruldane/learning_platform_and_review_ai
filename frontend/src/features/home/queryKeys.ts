/** Clés TanStack Query de l'accueil : aucune donnée du brief ni du fil, jamais. */
export const homeKeys = {
  brief: ["home", "brief"] as const,
  /** La première page du fil (la seule relue ; les pages plus anciennes sont lues à la demande). */
  activity: ["home", "activity"] as const,
  /** La relecture de fond des notifications. */
  notices: ["home", "notices"] as const,
} as const;
