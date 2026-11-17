const resets = new Set<() => void>();

/**
 * Inscrit une remise à zéro de ce qu'un module garde en mémoire (magasin, brouillon, stockage du
 * navigateur) en dehors de TanStack Query. Une feature n'en importe pas une autre : chacune
 * inscrit la sienne ici, et « Tout supprimer » les appelle toutes sans les connaître. Appelée au
 * chargement du module ; inscrire deux fois la même fonction n'en garde qu'une.
 */
export function onLocalReset(reset: () => void): void {
  resets.add(reset);
}

/** Vide tout ce qui est inscrit : rien de l'espace effacé ne doit rester affiché ni proposé. */
export function resetLocalState(): void {
  for (const reset of resets) reset();
}
