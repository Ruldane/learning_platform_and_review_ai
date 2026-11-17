/** Intervalle de relecture d'une séance ouverte (notes, fichiers, exécutions de Claude). */
export const LIVE_MS = 3000;

/**
 * Relit toutes les 3 s **tant que l'onglet est visible** : TanStack suspend l'intervalle quand la
 * page est cachée ou perd la visibilité (`refetchIntervalInBackground` est faux) et relit au
 * retour. Une relecture qui échoue garde les données déjà là.
 */
export const liveOptions = {
  refetchInterval: LIVE_MS,
  refetchIntervalInBackground: false,
} as const;
