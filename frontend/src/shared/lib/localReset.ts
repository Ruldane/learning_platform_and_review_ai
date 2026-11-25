const resets = new Set<() => void>();

/**
 * Registers a reset of what a module keeps in memory (store, draft, browser
 * storage) outside TanStack Query. A feature never imports another: each
 * registers its own here, and « Tout supprimer » calls them all without knowing them.
 * Runs at module load; registering the same function twice keeps only one.
 */
export function onLocalReset(reset: () => void): void {
  resets.add(reset);
}

/** Clears everything registered: nothing from the erased space should stay shown or offered. */
export function resetLocalState(): void {
  for (const reset of resets) reset();
}
