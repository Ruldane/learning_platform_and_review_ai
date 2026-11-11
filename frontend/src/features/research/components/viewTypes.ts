/** Types d'affichage des composants de la feature (voir `settings/components/viewTypes.ts`). */

/** Ce que l'utilisateur soumet pour un essai de l'Éclaireur. */
export interface ResearchBenchInput {
  query: string;
  /** Adresses http(s) à lire en plus de la recherche (5 au plus). */
  urls: string[];
}
